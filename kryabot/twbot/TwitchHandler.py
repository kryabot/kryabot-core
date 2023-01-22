import asyncio
import logging
import aioschedule
from typing import List, Dict
from datetime import datetime

from api.twitch_events import EventSubType, EventSubStatus
from object.ApiHelper import ApiHelper
from object.Base import Base
from object.BotConfig import BotConfig
from object.Database import Database
from object.Pinger import Pinger
from object.System import System
from twbot import ResponseAction
from twbot.command.CommandBase import CommandBase
from twbot.object.Channel import Channel
from twbot.object.ChannelCache import ChannelCache
from twbot.object.MessageContext import MessageContext
from twbot.object.Notice import Notice
from twbot.processor.CommandProcessor import CommandProcessor
from twbot.processor.EventProcessor import EventProcessor
from twbot.processor.NoticeProcessor import NoticeProcessor
from twbot.processor.PointProcessor import PointProcessor
from twbot.processor.Processor import Processor
from utils.array import split_array_into_parts, get_first
from utils import redis_key
from utils import schedule as scheduler_utils
from utils.json_parser import json_to_dict


class TwitchHandler(Base):
    def __init__(self, loop):
        self.logger = logging.getLogger('krya.twitch')
        self.logger.info('Initiating bot')
        self.loop = loop or asyncio.get_event_loop()
        self.cfg: BotConfig = BotConfig.get_instance()
        self.db: Database = Database.get_instance()
        self.api: ApiHelper = ApiHelper.get_instance()
        self.viewer_list: List = []
        self.admins: List = []
        self.tasks: List = []
        self.rate_list: List = []
        self.problems_to_report: List = []
        self.settings: List = []
        self.processors: List[Processor] = []
        self.bot_ep = EventProcessor.get_instance()
        self.bot_pp = PointProcessor.get_instance()
        self.bot_cp = CommandProcessor.get_instance()
        self.bot_np = NoticeProcessor.get_instance()
        self.global_commands: []

        ResponseAction.Response.redis = self.db.redis
        ResponseAction.Response._api = self.api
        CommandBase.database_instance = self.db
        CommandBase.api_instance = self.api
        CommandBase.logger_instance = self.logger

        self.processors.append(self.bot_ep)
        self.processors.append(self.bot_pp)
        self.processors.append(self.bot_cp)
        self.processors.append(self.bot_np)

        for proc in self.processors:
            proc.set_tools(self.logger, self.db, self.api)

    async def run_scheduler(self):
        self.logger.info("Started scheduler...")
        try:
            await aioschedule.run_all()

            while True:
                await asyncio.sleep(20)
                await aioschedule.run_pending()
        except Exception as ex:
            self.logger.exception(ex)
            self.problems_to_report.append(str(ex))

    async def init_scheduler(self):
        self.logger.info("Registering scheduler tasks...")
        aioschedule.every(1).hours.do(self.schedule_eventsub_register)
        aioschedule.every(10).minutes.do(self.sync_vips)
        aioschedule.every(10).minutes.do(self.sync_mods)
        aioschedule.every(10).minutes.do(self.sync_editors)

    async def start(self):
        await self.bot_data_update_all()
        await self.init_scheduler()
        await self.schedule_tasks()

        while True:
            await asyncio.sleep(60)

    async def bot_data_update_all(self)->None:
        # TODO: Split update by topics
        self.logger.info('Updating...')
        self.admins = await self.db.get_admins()
        self.settings = await self.db.get_settings()

        channels = await self.db.getAutojoinChannels()
        await self.update_channels(channels)
        for proc in self.processors:
            await proc.update()

    async def update_channels(self, channels)->None:
        id_list = []
        for ch in channels:
            id_list.append(ch['tw_id'])

        split_id_list = split_array_into_parts(id_list, 50)

        stream_datas = []
        for ids in split_id_list:
            self.logger.info('Requesting stream info for these IDs: {}'.format(ids))
            data = await self.api.twitch.get_stream_info_by_ids(ids)
            for info in data['data']:
                stream_datas.append(info)

        self.logger.info('Total live stream data size: {}'.format(len(stream_datas)))

        for ch in channels:
            try:
                new = False
                channel = ChannelCache.get(str(ch['channel_name']).lower())
                if channel is None:
                    channel = Channel(ch, self.logger, cfg=self.cfg, ah=self.api)
                    self.logger.info('Adding new channel to cache: {}'.format(channel.channel_name))
                    new = True

                for stream_info in stream_datas:
                    if int(stream_info['user_id']) == int(channel.tw_id):
                        self.logger.info('Updating live status for {}'.format(channel.channel_name))
                        channel.is_live = True
                        channel.stream_started = stream_info['started_at']

                ChannelCache.add(channel)

                if new:
                    # TODO: send join event to irc adapter?
                    pass
            except Exception as ex:
                self.logger.error('Failed to init channel: {}'.format(ch))
                self.logger.exception(ex)

    async def schedule_tasks(self):
        if self.tasks:
            return

        scheduler = self.loop.create_task(self.run_scheduler())
        eventsubs = self.loop.create_task(self.receive_twitch_events())
        listener = self.loop.create_task(self.db.redis.start_listener(self.redis_subscribe))
        triggers = scheduler_utils.schedule_task_periodically(5, self.timed_task_processor, logger=self.logger)
        ping = self.loop.create_task(Pinger(System.KRYABOT_TWITCH, self.logger, self.db.redis).run_task())

        self.tasks.append(triggers)
        self.tasks.append(listener)
        self.tasks.append(ping)
        self.tasks.append(scheduler)
        self.tasks.append(eventsubs)

    async def receive_twitch_events(self):
        self.logger.info('Starting queue listener: receive_twitch_events')
        try:
            while True:
                data = await self.db.redis.get_one_from_list_parsed(redis_key.get_twitch_eventsub_queue())
                if data:
                    self.loop.create_task(self.api.twitch_events.handle_event(event=data))
                else:
                    await asyncio.sleep(2)
        except Exception as any_ex:
            self.logger.exception(any_ex)
            await asyncio.sleep(5)

            # On error, Recreate this task again
            self.loop.create_task(self.receive_twitch_events())

    # List of subscribes executed during initialization
    async def redis_subscribe(self)->None:
        await self.db.redis.subscribe_event(redis_key.get_sync_topic(), self.sync_event)
        await self.db.redis.subscribe_event(redis_key.get_streams_forward_data(), self.on_stream_change)
        await self.db.redis.subscribe_event(redis_key.get_irc_topic_message(), self.on_message)
        await self.db.redis.subscribe_event(redis_key.get_irc_topic_notice(), self.on_usernotice)
        await self.db.redis.subscribe_event(redis_key.get_pubsub_topic(), self.on_channel_points)

    async def timed_task_processor(self)->None:
        for channel_key in ChannelCache.get_all().keys():
            if ChannelCache.get_all()[channel_key].can_trigger():
                await self.bot_cp.process_trigger(ChannelCache.get_all()[channel_key])
            else:
                self.logger.debug('Can not trigger yet for channel {}'.format(channel_key))

        if len(self.problems_to_report) > 0:
            await self.api.guardbot.report_problem('TwitchBot', 'Problem reporter', self.problems_to_report)
            self.problems_to_report = []

    async def update_channel_chat_activity_time(self, name: str)->None:
        try:
            ChannelCache.get(name).update_activity()
        except KeyError:
            self.logger.error('Failed to find cached channel for {}'.format(name))

    async def on_message(self, body):
        self.logger.debug(body)
        context = MessageContext(body)
        if context is None or context.channel is None:
            return

        db_info = await self.get_db_user(context.user.twitch_id, context.user.name, context.user.display_name)
        if db_info is None:
            self.logger.warning('Failed to get DB info for user: {}'.format(body))
            return

        context.set_user_db_info(db_info)
        self.loop.create_task(self.db.createMessage(context.channel.channel_id, db_info['user_id'], context.message))

        # Global/Custom command
        await self.bot_cp.process(context)

        # Treat bits as notice
        if context.has_bits():
            await self.bot_np.process_bits(context)

        # Chat Events
        await self.bot_ep.process_message(context)

        # Collect sub months info
        await self.task_save_badge_info(context)

    async def task_save_badge_info(self, context):
        try:
            if context.get_sub_months() > 0:
                await self.db.save_twitch_sub_count_to_cache(context.channel.tw_id, context.user.twitch_id, context.get_sub_months())
        except Exception as ex:
            self.logger.exception(ex)

    async def on_usernotice(self, body):
        self.logger.debug(body)
        context = MessageContext(body)
        if context is None or context.channel is None:
            return

        db_info = await self.get_db_user(context.user.twitch_id, context.user.name, context.user.display_name)
        if db_info is None:
            self.logger.warning('Failed to get DB info for user: {}'.format(body))
            return

        context.set_user_db_info(db_info)

        note = Notice(context.tags)
        await note.map()
        problems = await note.detect_unknown_tag()
        if len(problems) > 0:
            self.problems_to_report.append({'when': datetime.now(), 'topic': 'Notice tags', 'data': problems, 'raw_message': context.tags})

        if context.user.name is None:
            context.user.name = await note.get_user_name()

        if note.can_react():
            await self.bot_np.process(context=context, notice=note)

        count1 = await note.get_notice_count_int()
        count2 = await note.get_notice_count_int2()

        self.logger.info(context.tags)
        target_id = 0
        if note.msg_id == 'subgift':
            #self.logger.info(context.tags)
            # target_id is person who sent subgift
            target_id = db_info['user_id']
            db_user_receiver = await self.db.getUserRecordByTwitchId(note.msg_param_recipient_id)
            if len(db_user_receiver) == 0:
                await self.db.createUserRecord(note.msg_param_recipient_id, note.msg_param_recipient_user_name, note.msg_param_recipient_display_name)
                db_user_receiver = await self.db.getUserRecordByTwitchId(note.msg_param_recipient_id)
            db_info = db_user_receiver[0]

        await self.db.createNotice(context.channel.channel_id, db_info['user_id'], note.msg_id, note.msg_param_sub_plan,
                                   count1, count2, target_id)

    async def get_setting_value(self, key)->str:
        for setting in self.settings:
            if setting['setting_key'] == key:
                return setting['setting_value']

        return ''

    async def get_db_user(self, user_twitch_id, user_name, user_display_name):
        author_twitch_id = int(user_twitch_id)
        try:
            if author_twitch_id is None or author_twitch_id == 0:
                twitch_user_by_name = await self.api.twitch.get_users(usernames=[user_name])
                author_twitch_id = int(twitch_user_by_name['data'][0]['id'])

                if author_twitch_id is None or author_twitch_id == 0:
                    return
        except Exception as e:
            self.logger.error(
                'Tried to get tw id by name for {uname}, but failed: {err}'.format(uname=user_name, err=str(e)))
            return

        current_try = 0
        max_tries = 10

        while True:
            try:
                user = None
                users = await get_first(await self.db.getUserRecordByTwitchId(author_twitch_id))
                if users is None or users == [] or users == {}:
                    await self.db.createUserRecord(author_twitch_id, user_name, user_display_name)
                    user = await get_first(await self.db.getUserRecordByTwitchId(author_twitch_id, skip_cache=True))
                else:
                    user = users

                if user['name'] != user_name and user_name is not None or user['dname'] != user_display_name:
                    self.logger.debug('[{}] Updating user names, from [{} {}] to [{} {}]'.format(author_twitch_id, user['name'], user['dname'], user_name, user_display_name))
                    await self.db.updateUserTwitchName(user['user_id'], user_name, user_display_name, tw_user_id=author_twitch_id)
                return user
            except Exception as e:
                current_try += 1
                if current_try >= max_tries:
                    self.logger.error(
                        'Getting user from DB failed. Error: {err}, {aid}'.format(err=str(e), aid=author_twitch_id))
                    break

                await asyncio.sleep(current_try)
        return None

    async def get_db_channel(self, channel_name: str):
        channel_name = str(channel_name)
        channel = ChannelCache.get(channel_name)
        if channel is not None:
            return channel

        # DB
        try:
            channels = await self.db.getChannel(channel_name)
            if len(channels) == 0:
                await self.db.createChannelRecord(channel_name)
                channels = await self.db.getChannel(channel_name)
                channel = Channel(channels[0], log=self.logger, cfg=self.cfg, ah=self.api)
                ChannelCache.add(channel)
            return channel
        except Exception as e:
            self.logger.error('Getting channel from DB failed. Error: {err}'.format(err=str(e)))

        return None

    async def sync_event(self, msg):
        self.logger.info('Received sync event: {}'.format(msg))

        channel = ChannelCache.get_by_kb_user_id(msg['user_id'])
        if channel is None:
            self.logger.info('Skipping sync because did not find channel by user id {}'.format(msg['user_id']))
            return

        if msg['topic'] == 'twitch_command':
            await self.bot_cp.update(channel.channel_id)
        if msg['topic'] == 'twitch_channel':
            pass  # TODO: channel processor with join/leave mechanics
        if msg['topic'] == 'twitch_notice':
            await self.bot_np.update(channel.channel_id)
        if msg['topic'] == 'twitch_point_reward':
            await self.bot_pp.update(channel.channel_id)

    async def on_stream_change(self, data):
        self.logger.info(data)

        channel = ChannelCache.get_by_twitch_id(data['channel_id'])
        if channel is None:
            self.logger.info('Failed to find channel for twitch_id={}'.format(data['channel_id']))
            return

        answer = await channel.update_status(data)
        if answer is not None and len(answer) > 0:
            await channel.reply(answer)

    async def on_pubsub(self, data):
        try:
            # Response when subscribing new topic
            if data['type'] == 'RESPONSE':
                if len(data['error']) > 0:
                    self.logger.error('Pubsub error for nonce {}: {}'.format(data['nonce'], data['error']))
                else:
                    self.logger.info('Pubsub success for {}'.format(data['nonce']))
                return

            # Common pong response
            if data['type'] == 'PONG':
                return

            # Chat messages, bits, whispers
            if data['type'] == 'MESSAGE':
                if data['data']['topic'].startswith('channel-subscribe-events-v1.'):
                    pass  # Not used
                if data['data']['topic'].startswith('channel-bits-events-v1.'):
                    pass  # Not used
                if data['data']['topic'].startswith('channel-bits-events-v2.'):
                    pass  # Not used
                if data['data']['topic'].startswith('channel-bits-badge-unlocks.'):
                    pass  # Not used
                if data['data']['topic'].startswith('channel-commerce-events-v1.'):
                    pass  # Not used
                if data['data']['topic'].startswith('whispers.'):
                    pass  # Not used
                if data['data']['topic'].startswith('channel-points-channel-v1.'):
                    await self.pubsub_process_channel_points(data['data']['message'])
        except Exception as ex:
            self.logger.exception(ex)

    async def on_channel_points(self, data):
        if data['event']['status'] not in ['unfulfilled', 'fulfilled']:
            self.logger.info('Unexpected status: {} in event'.format(data['event']['status'], data['event']))
            return

        broadcaster_id = int(data['event']['broadcaster_user_id'])
        channel = ChannelCache.get_by_twitch_id(broadcaster_id)
        if channel is None:
            self.logger.error('Failed to find channel record for ID {}'.format(broadcaster_id))
            return

        user_id = int(data['event']['user_id'])
        user_login = data['event']['user_login']
        user_name = data['event']['user_name']

        db_user = await self.get_db_user(user_id, user_login, user_name)
        if db_user is None:
            # Retry, could be issue with sync/db
            await asyncio.sleep(3)
            db_user = await self.get_db_user(user_id, user_login, user_name)
            if db_user is None:
                self.logger.error('Failed to complete redemption, user not found. id: {} login: {}'.format(user_id, user_login))
                await channel.reply('@{} i failed to do redeption action for user {}. Please proceed manually.'.format(channel.channel_name, user_name))
                return

        self.logger.info('User {} redeemed {} on channel {}'.format(user_login, data['event']['reward']['title'], channel.channel_name))

        try:
            await self.bot_pp.process(channel, db_user, data['event'])
        except Exception as ex:
            self.logger.exception(ex)

    async def pubsub_process_channel_points(self, data):
        self.logger.info(data)

        try:
            data = json_to_dict(data)
        except Exception as ex:
            self.logger.exception(ex)
            return

        if data['type'] != 'reward-redeemed':
            self.logger.info('Unknown type received: {}'.format(data['type']))
            return

        redemption_data = data['data']['redemption']
        user = data['data']['redemption']['user']
        reward = data['data']['redemption']['reward']

        channel = ChannelCache.get_by_twitch_id(redemption_data['channel_id'])
        if channel is None:
            self.logger.error('Failed to find channel record for ID {}'.format(redemption_data['channel_id']))
            return

        # Find user data
        db_user = await self.get_db_user(user['id'], user['login'], user['display_name'])
        if db_user is None:
            await asyncio.sleep(3)
            db_user = await self.get_db_user(user['id'], user['login'], user['display_name'])
            if db_user is None:
                await channel.reply('@{} i failed to do redeption action for user {}. Please proceed manually.'.format(channel.channel_name, user['login']))
                self.logger.error('Failed to complete redemption, user not found. id: {} login: {}'.format(user['id'], user['login']))
                return

        self.logger.info('User {} redeemed {} on channel {}'.format(user['login'], reward['title'], channel.channel_name))

        try:
            await self.bot_pp.process(channel, db_user, redemption_data)
        except Exception as ex:
            self.logger.exception(ex)

    async def schedule_eventsub_register(self)->None:
        await asyncio.sleep(30)

        required_broadcaster_topics = [
            EventSubType.CHANNEL_SUBSCRIBE,
            EventSubType.CHANNEL_SUBSCRIBE_END,
            EventSubType.CHANNEL_SUBSCRIBE_GIFT,
            EventSubType.CHANNEL_SUBSCRIBE_MESSAGE,
            EventSubType.CHANNEL_RAID,
            EventSubType.CHANNEL_GOAL_BEGIN,
            EventSubType.CHANNEL_GOAL_END,
            EventSubType.CHANNEL_GOAL_PROGRESS,
            EventSubType.CHANNEL_POLL_BEGIN,
            EventSubType.CHANNEL_POLL_PROGRESS,
            EventSubType.CHANNEL_POLL_END,
            EventSubType.CHANNEL_POINTS_REDEMPTION_NEW,
            EventSubType.CHANNEL_POINTS_REDEMPTION_UPDATE,
            EventSubType.CHANNEL_HYPE_TRAIN_BEGIN,
            EventSubType.CHANNEL_HYPE_TRAIN_PROGRESS,
            EventSubType.CHANNEL_HYPE_TRAIN_END,
            EventSubType.CHANNEL_MOD_ADD,
            EventSubType.CHANNEL_MOD_REMOVE,
            EventSubType.CHANNEL_PREDICTION_BEGIN,
            EventSubType.CHANNEL_PREDICTION_END
        ]

        required_client_topics = [
            EventSubType.AUTH_GRANTED,
            EventSubType.AUTH_REVOKED,
        ]

        def filter_row(row, twitch_id)->bool:
            if 'broadcaster_user_id' in row['condition'] and int(row['condition']['broadcaster_user_id']) == int(twitch_id):
                return True
            if 'to_broadcaster_user_id' in row['condition'] and int(row['condition']['to_broadcaster_user_id']) == int(twitch_id):
                return True

            return False

        current_events = await self.api.twitch_events.get_all()
        for channel in ChannelCache.iter():
            auth = await self.db.getBotAuthByUserId(channel.user_id)
            if not auth:
                self.logger.info("Skipping eventsub check for user {} due to missing auth".format(channel.name))
                continue

            current_scopes = auth[0]['scope'].split(' ')
            channel_events = list(filter(lambda row: filter_row(row, channel.tw_id), current_events['data']))

            for topic in required_broadcaster_topics:
                have_scope = False
                if topic.scopes:
                    # Topic requires scopes in auth
                    for req_scope in topic.scopes:
                        if req_scope in current_scopes:
                            have_scope = True
                else:
                    have_scope = True

                if not have_scope:
                    self.logger.info("[{}] Skipping topic ${} creation due to missing scope".format(channel.tw_id, topic.key))
                    continue

                topic_event = next(filter(lambda row: row['type'] == topic.key, channel_events), None)
                if topic_event:
                    # topic was already registered, check status
                    status = EventSubStatus(topic_event['status'])
                    if status != EventSubStatus.ENABLED:
                        self.logger.info("[{}] Deleting not enabled event: {}".format(channel.tw_id, topic_event))
                        await self.api.twitch_events.delete(message_id=topic_event['id'])
                    else:
                        # status is enabled, we can skip to next topic
                        continue

                self.logger.info("[{}] Creating broadcaster topic ${}".format(channel.tw_id, topic.key))
                try:
                    if topic.eq(EventSubType.CHANNEL_RAID):
                        resp = await self.api.twitch_events.create(topic=topic, to_broadcaster_user_id=channel.tw_id)
                    else:
                        resp = await self.api.twitch_events.create(topic=topic, broadcaster_id=channel.tw_id)
                except Exception as ex:
                    self.logger.exception(ex)

        self.logger.info('Checking client topics...')
        for topic in required_client_topics:
            topic_event = next(filter(lambda row: row['type'] == topic.key, current_events['data']), None)
            if topic_event:
                status = EventSubStatus(topic_event['status'])
                if status != EventSubStatus.ENABLED:
                    self.logger.info("Deleting not enabled client event {}".format(topic_event))
                    await self.api.twitch_events.delete(message_id=topic_event['id'])
                else:
                    # status is enabled, we can skip to next topic
                    continue

            self.logger.info("Creating client topic ${}".format(topic.key))
            try:
                resp = await self.api.twitch_events.create_for_client(topic)
            except Exception as ex:
                self.logger.exception(ex)

    async def _sync(self, right_type: str, fetch_method: callable):
        # right_type: WHITELIST, BLACKLIST, SUDO
        for channel in ChannelCache.iter():
            changed: bool = False

            try:
                remote_rights = await fetch_method(broadcaster_id=channel.tw_id)
                current_rights = await self.db.get_tg_chat_special_rights(channel_id=channel.channel_id)
            except Exception as ex:
                self.logger.exception(ex)
                continue

            for remote_right in remote_rights['data']:
                # Available fields:
                # ['user_id'] ['user_name'] ['created_at']
                synced = False
                for current_right in current_rights:
                    if current_right['right_type'] != right_type:
                        continue
                    if remote_right['user_id'] != current_right['tw_id']:
                        continue
                    synced = True

                if not synced:
                    # add new
                    pass


            if changed:
                await self.db.get_all_tg_chat_special_rights(channel_id=channel.channel_id)

    async def sync_vips(self):
        await self._sync('WHITELIST', self.api.twitch.get_vips)

    async def sync_editors(self):
        await self._sync('SUDO', self.api.twitch.get_editors)


    async def sync_mods(self):
        pass
