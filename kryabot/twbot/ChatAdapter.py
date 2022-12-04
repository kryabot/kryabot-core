import asyncio
from datetime import datetime
import logging
from typing import Dict, List, Union

from object.Pinger import Pinger
from object.System import System
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
    async def event_pubsub(self, data):
        pass

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

        self.loop.create_task(Pinger(System.KRYABOT_TMI, self.logger, self.db.redis).run_task())

    async def on_update(self)->None:
        channels: Dict = await self.db.getAutojoinChannels()
        if channels is not None:
            for channel in channels:
                try:
                    jc = JoinedChannel(channel['channel_name'])
                    jc.working = True

                    self.logger.info('Joining to {} (working)'.format(jc.channel_name))
                    await self.join_channels([jc.channel_name])
                    self.channels.add(jc)
                    await asyncio.sleep(1)
                except Exception as ex:
                    self.logger.exception(ex)

            self.logger.info('Size of channels: {}'.format(len(self.channels.channels)))

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

        redis_task = self.loop.create_task(self.db.redis.start_listener(self.redis_subscribe))
        response_task = self.loop.create_task(self.listen_responses())

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
        self.in_update = False

    async def redis_subscribe(self)->None:
        self.logger.info('Subscribing redis topics...')

    async def event_message(self, message: Message)->None:
        context: Context = await self.get_context(message)

        await self.publish_message(context)

    async def event_mode(self, channel, user, status)->None:
        # DEPRECATED BY TWITCH
        self.logger.debug('MODE {} {} {}'.format(channel, user, status))

    async def event_join(self, user: User)->None:
        self.logger.debug('{} joined {}'.format(user.name, user.channel))
        await self.publish_movement('JOIN', user)

    async def event_part(self, user: User)->None:
        self.logger.debug('{} left {}'.format(user.name, user.channel))
        await self.publish_movement('PART', user)

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

    async def listen_responses(self)->None:
        while True:
            try:
                data = await self.db.redis.get_one_from_list_parsed(redis_key.get_irc_response_queue())
                if data is not None:
                    self.loop.create_task(self.process_response(data))
                    continue
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
