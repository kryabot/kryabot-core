import asyncio
from datetime import datetime
import logging
from typing import Dict, List, Union

from api.twitch import Twitch
from twbot.ResponseAction import ResponseAction
from twitchio import Context, Message, Channel, User
from twitchio.ext import commands
from object.Base import Base
from object.BotConfig import BotConfig
from object.Database import Database
from twitchio.ext.commands import CommandNotFound
from utils import redis_key
from utils import schedule


class ChatAdapter(Base, commands.Bot):
    def __init__(self):
        self.loop: asyncio.BaseEventLoop = asyncio.get_event_loop()
        self.cfg: BotConfig = BotConfig()
        self.db: Database = Database(self.loop, 3, cfg=self.cfg)
        self.logger: logging = logging.getLogger('krya.irc')
        self.tasks: List = []
        self.channels = Channels()
        self.response: ResponseAction = None
        self.in_update: bool = False

        super().__init__(irc_token=self.cfg.getTwitchConfig()['IRC_PASS'],
                         nick=self.cfg.getTwitchConfig()['IRC_NICK'].lower(),
                         initial_channels=[self.cfg.getTwitchConfig()['IRC_NICK'].lower()],
                         prefix=self.cfg.getTwitchConfig()['GLOBAL_PREFIX'],
                         loop=self.loop,
                         modes=("commands", "tags"))

    async def event_pubsub(self, data):
        pass

    async def on_update(self)->None:
        channels: Dict = await self.db.getAutojoinChannels()
        if channels is not None:
            for channel in channels:
                try:
                    jc = JoinedChannel(channel['channel_name'])
                    jc.working = True
                    jc.scan_in_spam_detector = bool(channel['scan_messages'] > 0)
                    jc.on_detection_enable_sub_only_chat = bool(channel['scan_messages'] > 1)
                    jc.on_detection_ban_self = bool(channel['on_spam_detect'] > 0)
                    jc.on_detection_ban_other = bool(channel['on_spam_detect'] > 2)

                    self.logger.info('Joining to {} (working)'.format(jc.channel_name))
                    await self.join_channels([jc.channel_name])
                    self.channels.add(jc)
                    await asyncio.sleep(0.5)
                except Exception as ex:
                    self.logger.exception(ex)

        await self.resubstribe_pubsub()

    async def disconnect(self):
        self.logger.info('Disconnecting...')
        for task in self.tasks:
            await schedule.cancel_scheduled_task(task=task)

        self._ws.teardown()
        await self.db.redis.redis_pool.close()
        await self.db.connection_close()

    async def schedule_tasks(self)->None:
        # If array has elements, means we already started tasks, no need to duplicate them
        if self.tasks:
            return

        auto_task = schedule.schedule_task_periodically(wait_time=redis_key.ttl_hour,
                                                        func=self.auto_join_channels,
                                                        logger=self.logger)

        redis_task = self.loop.create_task(self.db.redis.start_listener(self.redis_subscribe))
        response_task = self.loop.create_task(self.listen_responses())

        self.tasks.append(auto_task)
        self.tasks.append(redis_task)
        self.tasks.append(response_task)

    async def event_ready(self)->None:
        if self.in_update:
            return

        self.in_update = True

        if self.response is None:
            self.response = ResponseAction(self._ws, self.logger)

        await self.on_update()
        await self.schedule_tasks()
        self.logger.info(f'Adapter is ready now, {self.nick}')
        await self._ws.send_privmsg(self.nick, '/w {owner} IRC adapter started'.format(owner=self.cfg.getInstanceConfig()['OWNER']))
        self.in_update = False

    async def on_spam_detector_response(self, body: Dict)->None:
        self.logger.info(body)

        channel: Channel = self._ws._channel_cache[body['channel']]['channel']
        bot: User = self._ws._channel_cache[body['channel']]['bot']
        if not bot.is_mod:
            self.logger.info('Ignoring response to channel {} because I not mod!'.format(channel.name))
            return

        jc = self.channels.get_by_name(channel.name)
        action = body['action']

        if action == 'message':
            await channel.send(body['text'])
        elif action == 'ban':
            if body['users']:
                for event in body['users']:
                    if jc.on_detection_ban_self:
                        await channel.ban(event['sender'], reason="Spambot")

                    # TODO: ban queue, currently ban in onlyashaa channel.
                    await self._ws.send_privmsg('olyashaa', ".ban {} Spambot, detected in channel {}".format(event['sender'], body['channel']))
        elif action == 'unban':
            if body['users']:
                for event in body['users']:
                    await channel.unban(event['sender'])
        elif action == 'detection':
            if jc.on_detection_enable_sub_only_chat:
                if body['status'] == 1:
                    await channel.send(".subscribers")
                    await channel.send("Enabling subonly chat to avoid spam!")
                elif body['status'] == 0:
                    await channel.send(".subscribersoff")
                    await channel.send("Disabling subonly chat!")

    async def redis_subscribe(self)->None:
        self.logger.info('Subscribing redis topics...')
        await self.db.redis.subscribe_event(redis_key.get_twitch_spam_detector_response_topic(), self.on_spam_detector_response)
        await self.db.redis.subscribe_event(redis_key.get_token_update_topic(), self.on_token_update)

    async def on_token_update(self, msg):
        if 'channel:read:redemptions' in msg['scope']:
            self.logger.info('PubSub redemptions resubscribe for user {}'.format(msg['tw_id']))
            await self.pubsub_subscribe(msg['token'], 'channel-points-channel-v1.{}'.format(msg['tw_id']))

    async def event_message(self, message: Message)->None:
        context: Context = await self.get_context(message)

        await self.publish_message(context)
        await self.send_to_spam_detector(context)

    async def event_mode(self, channel, user, status)->None:
        # DEPRECATED BY TWITCH
        self.logger.debug('MODE {} {} {}'.format(channel, user, status))

    async def event_join(self, user: User)->None:
        self.logger.debug('{} joined {}'.format(user.name, user.channel))
        await self.publish_movement('JOIN', user)

    async def event_part(self, user: User)->None:
        self.logger.debug('{} left {}'.format(user.name, user.channel))
        await self.publish_movement('PART', user)

    async def event_raw_pubsub(self, data):
        await self.db.redis.publish_event(redis_key.get_pubsub_topic(), data)

    async def event_custom_raw_usernotice(self, irc)->None:
        context: Context = await self.get_context(irc)

        await self.publish_notice(context)

    async def event_channel_notice(self, channel: Channel, tags: Dict):
        pass

    async def event_roomstate(self, channel: Channel, tags: Dict):
        pass

    async def event_command_error(self, ctx, error)->None:
        if isinstance(error, CommandNotFound):
            return

        self.logger.exception(error)

    async def publish_message(self, context: Context)->None:
        body = {
            "channel": str(context.channel.name),
            "channel_id": context.author.tags.get('room-id', 0),
            #"chatters": context.channel.chatters,
            "sender": str(context.author.name),
            "display_name": str(context.author.display_name),
            "sender_id": context.author.id,
            "tags": context.author.tags,
            "message": str(context.message.content),
            "ts": context.message.timestamp,
        }

        await self.db.redis.publish_event(redis_key.get_irc_topic_message(), body)

    async def publish_notice(self, context: Context)->None:
        body = {
            "channel": context.channel.name,
            "channel_id": context.author.tags.get('room-id', 0),
            "sender": context.author.name,
            "display_name": context.author.display_name,
            "sender_id": context.author.id,
            "tags": context.author.tags,
            "message": context.message.content,
            "ts": context.message.timestamp,
        }

        await self.db.redis.publish_event(redis_key.get_irc_topic_notice(), body)

    async def publish_movement(self, type: str, user: User)->None:
        body = {
            "channel": user.channel.name,
            "type": type,
            "sender": user.name,
            "display_name": user.display_name,
        }

        await self.db.redis.publish_event(redis_key.get_irc_topic_part(), body)

    async def send_to_spam_detector(self, context: Context):
        # Skip such users
        if context.author.is_mod or context.author.is_subscriber or context.author.is_turbo:
            return

        # If user has any badge, skip
        if context.author.badges != {}:
            return

        body={
            "channel": context.channel.name,
            "sender": context.author.name,
            "twitch_emotes": context.author.tags.get('emotes', None),
            "message": context.message.content,
            "ts": datetime.utcnow()
        }
        await self.db.redis.publish_event(redis_key.get_twitch_spam_detector_request_topic(), body)

    async def auto_join_channels(self)->None:
        self.logger.info('Auto join check...')
        api = Twitch(self.db.redis, cfg=self.cfg)

        streams = await api.get_streams(first=100, language='ru')
        for stream in streams['data']:
            await asyncio.sleep(0.3)
            existing = self.channels.get_by_name(stream['user_name'])
            if existing:
                existing.touch()
            else:
                new = JoinedChannel(stream['user_name'])
                self.logger.info('Joining to {} (auto)'.format(new.channel_name))
                self.channels.add(new)
                try:
                    await self.join_channels([new.channel_name])
                except Exception as ex:
                    self.logger.exception(ex)

        for channel in self.channels.channels:
            if channel.can_leave():
                self.logger.info('Leaving inactive channel {}'.format(channel.channel_name))
                await self.part_channels([channel.channel_name])

    async def resubstribe_pubsub(self)->None:
        auths = await self.db.getBotAuths()
        for auth in auths:
            if 'channel:read:redemptions' in auth['scope']:
                self.logger.info('Resubscribing pubsub redepntions for channel {} {}'.format(auth['tw_id'], auth['token']))
                await self.pubsub_subscribe(auth['token'], 'channel-points-channel-v1.{}'.format(auth['tw_id']))

    async def listen_responses(self)->None:
        while True:
            try:
                data = await self.db.redis.get_one_from_list_parsed(redis_key.get_irc_response_queue())
                if data is not None:
                    self.loop.create_task(self.process_response(data))
            except Exception as ex:
                self.logger.exception(ex)

            await asyncio.sleep(1/100)

    async def process_response(self, data)->None:
        self.logger.info(data)
        jc: JoinedChannel = self.channels.get_by_name(data['channel'])
        if jc is None or not jc.working:
            self.logger.info('skip1')
            return

        try:
            await self.response.process(data)
        except Exception as ex:
            self.logger.exception(ex)


class JoinedChannel(Base):
    def __init__(self, channel_name):
        self.channel_name: str = channel_name
        self.scan_in_spam_detector: bool = True
        self.on_detection_ban_self: bool = False
        self.on_detection_ban_other: bool = False
        self.on_detection_enable_sub_only_chat: bool = False
        self.working: bool = False
        self.mod: bool = False
        self.slow: int = 0
        self.emote_only: bool = False
        self.followers_only: bool = False
        self.follow_limit = None
        self.r9k: bool = False
        self.sub_only = False
        self.last_update: datetime = datetime.utcnow()

    def touch(self)->None:
        self.last_update = datetime.utcnow()

    def can_leave(self)->bool:
        # TODO: datetime checking
        return not self.working and False


class Channels(Base):
    def __init__(self):
        self.channels: List[JoinedChannel] = []

    def add(self, channel: JoinedChannel)->None:
        existing = self.get_by_name(channel_name=channel.channel_name)
        if existing:
            self.channels.remove(existing)

        self.channels.append(channel)

    def get_by_name(self, channel_name: str)->Union[JoinedChannel, None]:
        for ch in self.channels:
            if str(ch.channel_name).lower() == str(channel_name).lower():
                return ch

        return None
