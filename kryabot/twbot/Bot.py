from typing import List

from twbot.processor.EventProcessor import EventProcessor
from twbot.processor.CommandProcessor import CommandProcessor
from twbot.processor.PointProcessor import PointProcessor
from twitchio.ext import commands
from object.Database import Database
from twbot.object.Channel import Channel
from twbot.processor.NoticeProcessor import NoticeProcessor
from object.BotConfig import BotConfig
from object.ApiHelper import ApiHelper
from twbot.object.Notice import Notice
from datetime import datetime, timedelta

from twitchio.ext.commands import CommandNotFound
from utils import redis_key
import asyncio
import logging
from utils.array import get_first
from utils.json_parser import json_to_dict
import queue


class Bot(commands.Bot):
    def __init__(self, loop=None):
        self.cfg = BotConfig()
        self.db = Database(loop, self.cfg.getTwitchConfig()['MAX_SQL_POOL'])
        self.custom_working_channels: List[Channel] = []
        self.bot_admins = []
        self.bot_auto_join_channels = []
        self.bot_settings = []
        self.bot_api_helper = ApiHelper(redis=self.db.redis, cfg=self.cfg)
        self.viewer_list = []
        self.bot_in_update = False
        self.is_silent = False
        self.logger = logging.getLogger('krya.twitch')
        self.logger.info('Initiating bot')
        self.custom_loops_started = False
        self.rate_list = []
        self.last_webhook_resubscribe = None
        self.webhook_queue = queue.Queue()
        self.webhook_queue_reader_started = False
        self.problems_to_report = []

        self.bot_ep = EventProcessor(self.is_silent, self.logger)

        super().__init__(irc_token=self.cfg.getTwitchConfig()['IRC_PASS'],
                         client_id=self.cfg.getTwitchConfig()['API_KEY'],
                         nick=self.cfg.getTwitchConfig()['IRC_NICK'].lower(),
                         prefix=self.cfg.getTwitchConfig()['GLOBAL_PREFIX'],
                         initial_channels=[],
                         webhook_server=self.cfg.getTwitchWebhookConfig()['ENABLED'],
                         callback=self.cfg.getTwitchWebhookConfig()['CALLBACK'],
                         port=self.cfg.getTwitchWebhookConfig()['PORT'],
                         local_host=self.cfg.getTwitchWebhookConfig()['HOST'],
                         loop=loop
                         )
        self.processors = []
        self.bot_pp = PointProcessor()
        self.bot_cp = CommandProcessor()
        self.bot_np = NoticeProcessor()

        self.processors.append(self.bot_pp)
        self.processors.append(self.bot_cp)
        self.processors.append(self.bot_np)

        #self.processors = [proc.set_tools(self.logger, self.db, self.bot_api_helper, self._ws) for proc in self.processors]
        for proc in self.processors:
            proc.set_tools(self.logger, self.db, self.bot_api_helper, self._ws)

    async def bot_data_update_all(self):
        # TODO: Split update by topics
        self.logger.info('Bot data update')
        self.bot_in_update = True
        self.bot_admins = await self.db.getAdmins()

        self.bot_auto_join_channels = await self.db.getAutojoinChannels()
        self.bot_settings = await self.db.getSettings()

        for proc in self.processors:
            await proc.update()

        await self.bot_auto_join()

        self.bot_in_update = False

    async def bot_auto_join(self):
        # Join channels and set stream info
        for ch in self.bot_auto_join_channels:
            try:
                new_channel = Channel(ch, self.logger, cfg=self.cfg, ah=self.bot_api_helper)
                # Skip if already joined
                for exist_channel in self.custom_working_channels:
                    if exist_channel.channel_name == new_channel.channel_name:
                        break

                await self.join_channels([new_channel.channel_name])
                flow_data = await self.db.get_stream_flows(new_channel.tw_id)
                self.logger.info(flow_data)
                if len(flow_data) > 0:
                    flow_data = flow_data[-1]['data']
                else:
                    flow_data = []
                    
                self.logger.info('updating status')
                await new_channel.update_status(flow_data, notify=False, db=self.db)
                await self.update_channel_cache(new_channel)

                self.logger.info('Auto join to channel {chname} successful'.format(chname=new_channel.channel_name))
            except Exception as e:
                self.logger.error('Auto join to channel {chname} failed. Reason: {r}'.format(chname=ch['channel_name'],r=str(e)))
                continue

    async def timed_task_processor(self):
        # Make sure only one timed_task_processor is running
        if self.custom_loops_started is True:
            return

        self.custom_loops_started = True
        while True:
            await asyncio.sleep(5)

            try:
                for channel in self.custom_working_channels:
                    if channel.can_trigger():
                        # self.logger.debug('Searching trigger for channel {}'.format(channel.channel_name))
                        await self.bot_cp.process_trigger(channel)
                    else:
                        self.logger.debug('Can not trigger yet for channel {}'.format(channel.channel_name))

                if len(self.problems_to_report) > 0:
                    await self.bot_api_helper.guardbot.report_problem('TwitchBot', 'Problem reporter', self.problems_to_report)
                    self.problems_to_report = []

            except Exception as ex:
                self.logger.exception(ex)

    # Resubscribe pubsub when token changed
    async def main_token_update(self, msg):
        if 'channel:read:redemptions' in msg['scope']:
            self.logger.info('PubSub redemptions resubscribe for user {}'.format(msg['tw_id']))
            await self.pubsub_subscribe(msg['token'], 'channel-points-channel-v1.{}'.format(msg['tw_id']))

    # List of subscribes executed during initialization
    async def redis_subscribe(self):
        await self.db.redis.subscribe_event(redis_key.get_token_update_topic(), self.main_token_update)
        await self.db.redis.subscribe_event(redis_key.get_sync_topic(), self.sync_event)

    # Events don't need decorators when subclassed
    async def event_ready(self):
        await self.bot_data_update_all()
        self.loop.create_task(self.timed_task_processor())
        self.loop.create_task(self.webhook_queue_reader())

        await self.resubstribe_pubsub()
        await self.resubscribe_webhooks()

        self.loop.create_task(self.db.redis.start_listener(self.redis_subscribe))

        self.logger.info(str(f'Bot is ready now, {self.nick}'))
        await self._ws.send_privmsg(self.nick, '/w {owner} Bot started'.format(owner=self.cfg.getInstanceConfig()['OWNER']))

    async def resubstribe_pubsub(self):
        auths = await self.db.getBotAuths()
        for auth in auths:
            if 'channel:read:redemptions' in auth['scope']:
                self.logger.info('Resubscribing pubsub redepntions for channel {} {}'.format(auth['tw_id'], auth['token']))
                await self.pubsub_subscribe(auth['token'], 'channel-points-channel-v1.{}'.format(auth['tw_id']))

    async def resubscribe_webhooks(self):
        # Auto-refresh stream webbooks each 7 days.
        if not self.last_webhook_resubscribe is None and self.last_webhook_resubscribe > datetime.now() - timedelta(days=7):
            return

        self.last_webhook_resubscribe = datetime.now()
        self.logger.info('>>> Subscribing webhook stream events')
        for ch in self.custom_working_channels:
            if ch.tw_id == 0:
                continue

            await asyncio.sleep(1)
            self.logger.info('> ' + ch.channel_name)
            # Json error is returned as no json actually is returned
            try:
                await self.bot_ep.twitch_api.webhook_subscribe_stream(user_id=ch.tw_id, channel_name=ch.channel_name)
            except Exception as e:
                pass

    async def update_channel_chat_activity_time(self, name):
        for ch in self.custom_working_channels:
            if ch.matches(name):
                ch.update_activity()

    async def event_message(self, message):
        irc_user = await self.get_context(message)

        # Do not react to own messages
        if irc_user.author.name.lower() != self.cfg.getTwitchConfig()['IRC_NICK'].lower():
            await self.update_channel_chat_activity_time(irc_user.channel.name)
			
        db_user = await self.get_db_user(irc_user.author)
        db_channel = await self.get_db_channel(irc_user.channel)

        # Do not do anything if failed to get channel or user.
        if db_user is None or db_channel is None:
            return

        # Custom commands
        if message.content.lower().startswith(db_channel.command_symbol):
            await self.bot_cp.process(irc_user, db_user, db_channel)

        try:
            bc = irc_user.message.tags['bits']
        except Exception as e:
            bc = 0

        if bc > 0:
            await self.bot_np.process_bits(irc_data=irc_user, db_channel=db_channel, db_user=db_user, count=bc)

        # Global commands
        await self.handle_commands(message)

        # Chat Events
        await self.bot_ep.process_message(irc_data=irc_user)

        # Collect sub months info
        await self.task_save_badge_info(irc_user)

    async def get_setting_value(self, key):
        for setting in self.bot_settings:
            if setting['setting_key'] == key:
                return setting['setting_value']
        return ''

    async def get_db_user(self, author):
        return await self.get_db_user_inputs(author.id, author.name)

    async def get_db_user_inputs(self, author_twitch_id, author_twitch_name):
        author_twitch_id = int(author_twitch_id)
        try:
            if author_twitch_id is None or author_twitch_id == 0:
                twitch_user_by_name = await self.bot_api_helper.twitch.get_user_by_name(author_twitch_name)
                author_twitch_id = twitch_user_by_name['users'][0]['_id']

                if author_twitch_id is None or author_twitch_id == 0:
                    return
        except Exception as e:
            self.logger.error('Tried to get tw id by name for {uname}, but failed: {err}'.format(uname=author_twitch_name, err=str(e)))
            return

        current_try = 0
        max_tries = 10

        while True:
            try:
                users = await get_first(await self.db.getUserRecordByTwitchId(author_twitch_id))
                if users is None or users == [] or users == {}:
                    await self.db.createUserRecord(author_twitch_id, author_twitch_name)
                    users = await get_first(await self.db.getUserRecordByTwitchId(author_twitch_id, skip_cache=True))
                    return users
                else:
                    return users
            except Exception as e:
                current_try += 1
                if current_try >= max_tries:
                    self.logger.error('Getting user from DB failed. Error: {err}, {aid}'.format(err=str(e), aid=author_twitch_id))
                    break

                await asyncio.sleep(current_try)
        return None

    async def get_db_channel(self, irc_channel):
        # Cached
        for ch in self.custom_working_channels:
            if ch.channel_name == irc_channel.name:
                return ch

        # DB
        try:
            channels = await self.db.getChannel(irc_channel.name)
            if len(channels) == 0:
                await self.db.createChannelRecord(irc_channel.name)
                channels = await self.db.getChannel(irc_channel.name)

            await self.update_channel_cache(channels[0])
            return channels[0]
        except Exception as e:
            self.logger.error('Getting channel from DB failed. Error: {err}'.format(err=str(e)))

        return None

    async def update_channel_cache(self, parsed_channel):
        if parsed_channel is None:
            return

        i = 0
        j = 0
        for ch in self.custom_working_channels:
            i = i + 1
            if ch.channel_name == parsed_channel.channel_name:
                j = i
                break

        if j > 0:
            self.custom_working_channels[j-1] = parsed_channel
            return

        self.custom_working_channels.append(parsed_channel)

    async def event_custom_raw_usernotice(self, irc):
        irc_data = await self.get_context(irc)

        note = Notice(irc_data.message.tags)
        await note.map()
        problems = await note.detect_unknown_tag()
        if len(problems) > 0:
            self.problems_to_report.append({'when': datetime.now(), 'topic': 'Notice tags', 'data': problems, 'raw_message': irc_data.message.tags})

        if irc_data.author.name is None:
            irc_data.author._name = await note.get_user_name()

        db_user = await self.get_db_user(irc_data.author)
        db_channel = await self.get_db_channel(irc_data.channel)

        if db_user is None:
            self.logger.error('empty user: ' + irc_data.author.name)
            return

        if db_channel is None:
            self.logger.error('empty channel')
            return

        await self.bot_np.process(irc_data=irc_data, channel=db_channel, db_user=db_user, notice=note)

        count1 = await note.get_notice_count_int()
        count2 = await note.get_notice_count_int2()

        target_id = 0
        if note.msg_id == 'subgift':
            self.logger.info(irc_data.message.tags)
            # target_id is person who sent subgift
            target_id = db_user['user_id']
            db_user_receiver = await self.db.getUserRecordByTwitchId(note.msg_param_recipient_id)
            if len(db_user_receiver) == 0:
                await self.db.createUserRecord(note.msg_param_recipient_id, note.msg_param_recipient_user_name)
                db_user_receiver = await self.db.getUserRecordByTwitchId(note.msg_param_recipient_id)
            db_user = db_user_receiver[0]

        await self.db.createNotice(db_channel.channel_id, db_user['user_id'], note.msg_id, note.msg_param_sub_plan,
                                   count1, count2, target_id)

    async def event_command_error(self, ctx, error):
        if isinstance(error, CommandNotFound):
            return

        self.logger.exception(error)

    @commands.command(name='finishevent', aliases=['roll'])
    async def global_finish_event(self, ctx):
        if self.bot_cp.get_access_level(ctx) < 6:
        #if not await self.bot_cp.is_admin(ctx.author.name):
            return
        id = 0
        for ch in self.custom_working_channels:
            if ch.channel_name == ctx.channel.name:
                id = ch.tw_id

        await self.bot_ep.finish_event(ctx, id)

    @commands.command(name='cancelevent', aliases=['ce'])
    async def global_cancel_event(self, ctx):
        if self.bot_cp.get_access_level(ctx) < 6:
        #if not await self.bot_cp.is_admin(ctx.author.name):
            return

        await self.bot_ep.cancel_event(ctx)

    async def get_word_list(self, content):
        try:
            word_list = content.split()
            if len(word_list) > 1:
                del word_list[0]
                return ' '.join(word_list)
            elif len(word_list) == 1:
                return word_list[1]
            else:
                return None
        except:
            return None

    @commands.command(name='startevent', aliases=['ae'])
    async def global_start_event(self, ctx):
        if self.bot_cp.get_access_level(ctx) < 6:
        #if not await self.bot_cp.is_admin(ctx.author.name):
            return

        key = await self.get_word_list(ctx.message.content)
        if key is None:
            return

        runtime = 0
        await self.bot_ep.start_event(irc_data=ctx, keyword=key, runtime=runtime, event_type=3)

    @commands.command(name='startsubonlyevent', aliases=['se'])
    async def global_start_sub_event(self, ctx):
        if self.bot_cp.get_access_level(ctx) < 6:
        #if not await self.bot_cp.is_admin(ctx.author.name):
            return

        key = await self.get_word_list(ctx.message.content)
        if key is None:
            return

        runtime = 0
        await self.bot_ep.start_event(irc_data=ctx, keyword=key, runtime=runtime, event_type=2)

    @commands.command(name='startsubgiftevent', aliases=['ge'])
    async def global_start_subgift_event(self, ctx):
        if self.bot_cp.get_access_level(ctx) < 6:
            self.logger.info('User {u} wanted to star event but he is not an admin!'.format(u=ctx.author.name))
            return

        key = await self.get_word_list(ctx.message.content)
        if key is None:
            self.logger.info('User {u} wanted to star event but keyword is missing!'.format(u=ctx.author.name))
            return

        runtime = 0
        await self.bot_ep.start_event(irc_data=ctx, keyword=key, runtime=runtime, event_type=1)

    @commands.command(name='spam')
    async def global_spam_command(self, ctx):
        async def get_word_count(list, idx):
            try:
                return int(list[idx])
            except:
                return 0

        if ctx.author.is_mod != True and ctx.author.name.lower() != self.cfg.getInstanceConfig()['OWNER'].lower() and ctx.author.name.lower() != ctx.channel.name.lower():
            return

        default_message_count = 10
        max_count = 20
        wlist = ctx.message.content.split()

        try:
            count = await get_word_count(wlist, 1)
            if count > 0:
                del wlist[1]

            if count is None or count == 0 or count > max_count:
                count = default_message_count

            del wlist[0]
            spam_text = ' '.join(wlist)

            if len(spam_text) > 0 and self.is_silent != True:
                for x in range(count):
                    await ctx.send(spam_text)
        except Exception as e:
            self.logger.error('global_spam_command: %s', str(e))
            return

    @commands.command(name='startrate', aliases=['srate'])
    async def global_rate_start(self, ctx):
        if self.is_silent is True:
            return

        db_channel = await self.get_db_channel(ctx.channel)
        if db_channel is None:
            return

        rate_event = None
        for re in self.rate_list:
            if re['tw_id'] == db_channel.tw_id:
                rate_event = re

        if rate_event['active'] == 1:
            await ctx.send('Rate event already active! Finish previous one if you want to start new one.')
            return

        # TODO

        pass

    @commands.command(name='finishrate', aliases=['frate'])
    async def global_rate_finish(self, ctx):
        if self.is_silent is True:
            return
        # TODO

        pass

    @commands.command(name='unlinktelegram')
    async def global_unlink(self, ctx):
        try:
            if ctx.author.id is None or ctx.author.id == 0:
                await ctx.send('{} currently i am not feeling well, please try bit later.'.format(ctx.author.name))
                return

            linkage_data = await self.db.getLinkageDataByTwitchId(ctx.author.id)
            if linkage_data is None or len(linkage_data) == 0 or linkage_data[0]['response_id'] is None or linkage_data[0]['response_time'] is None:
                await ctx.send('{} you do not have active telegram link!'.format(ctx.author.name))
                return

            day_limit = 30
            diff = datetime.now() - linkage_data[0]['response_time']
            if diff.days < day_limit:
                await ctx.send('{} sorry, but can not unlink telegram account, yet! You can unlink only after {} day(s)'.format(ctx.author.name, day_limit - diff.days))
                return

            await self.db.deleteTelegramLink(linkage_data[0]['user_id'])
            await self.bot_api_helper.guardbot.notify_tg_unlink(linkage_data[0]['user_id'], ctx.author.id, linkage_data[0]['tg_id'])
            await ctx.send('{} successfully unlinked!'.format(ctx.author.name))
        except Exception as e:
            self.logger.error('Unlink error: {}'.format(str(e)))

    async def event_raw_data(self, data):
        pass

    # Do not do anything in event_webhook because it runs in different loop (no access to db/redis)
    async def event_webhook(self, data, params=None):
        self.logger.info('{p}: {d}'.format(p=params, d=data))
        if params is None:
            return

        topic = 'streams'
        try:
            channel_name = params.query['channel']
            topic = params.query['topic']
        except Exception as e:
            self.logger.error("{err}".format(err=str(e)))
            return

        task = {'channel_name': channel_name, 'topic': topic, 'data': data['data']}
        self.webhook_queue.put(task)

    async def process_webhook_stream(self, channel_name, data):
        for ch in self.custom_working_channels:
            if ch.channel_name.lower() == channel_name.lower():
                try:
                    answer = await ch.update_status(data, db=self.db)
                    if answer is not None and len(answer) > 0:
                        await self._ws.send_privmsg(ch.channel_name, answer)
                except Exception as e:
                    self.logger.error(e)

    async def process_webhook_sub(self, channel_name, data):
        try:
            channel = await self.get_db_channel(channel_name)
            data = data[0]
            event_data = data['event_data']

            user = await self.get_db_user_inputs(event_data['user_id'], event_data['user_name'])
            if user is None:
                self.logger.info('Failed to found user for received sub event. User id: {}'.format(event_data['user_id']))

            await self.db.saveTwitchSubEvent(channel['channel_id'],
                                             user['user_id'],
                                             data['id'],
                                             data['event_type'],
                                             data['event_timestamp'],
                                             event_data['is_gift'],
                                             event_data['tier'],
                                             event_data['message'])
        except Exception as e:
            self.logger.error(str(e))

    async def webhook_queue_reader(self):
        if self.webhook_queue_reader_started is True:
            return

        self.webhook_queue_reader_started = True
        while True:
            while self.webhook_queue.empty():
                await asyncio.sleep(0.5)

            task = self.webhook_queue.get()

            if task['topic'] == 'streams':
                await self.process_webhook_stream(task['channel_name'], task['data'])
            if task['topic'] == 'subscriptions':
                await self.process_webhook_sub(task['channel_name'], task['data'])

            self.webhook_queue.task_done()

    async def task_save_badge_info(self, irc_data):
        try:
            if irc_data.author.subscriber_months:
                await self.db.save_twitch_sub_count_to_cache(irc_data.author.from_channel_id, irc_data.author.id, irc_data.author.subscriber_months)
        except Exception as ex:
            self.logger.exception(ex)

    async def event_raw_pubsub(self, data):
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

        # Find channel data
        db_channel = None
        for ch in self.custom_working_channels:
            if ch.tw_id == redemption_data['channel_id']:
                db_channel = ch

        if db_channel is None:
            self.logger.error('Failed to find channel record for ID {}'.format(redemption_data['channel_id']))
            return

        # Find user data
        db_user = await self.get_db_user_inputs(user['id'], user['login'])
        if db_user is None:
            await asyncio.sleep(3)
            db_user = await self.get_db_user_inputs(user['id'], user['login'])
            if db_user is None:
                await self._ws.send_privmsg(db_channel.channel_name, content='@{} i failed to do redeption action for user {}. Please proceed manually.'.format(db_channel.channel_name, user['login']))
                self.logger.error('Failed to complete redemption, user not found. id: {} login: {}'.format(user['id'], user['login']))
                return

        self.logger.info('User {} redeemed {} on channel {}'.format(user['login'], reward['title'], db_channel.channel_name))

        try:
            await self.bot_pp.process(db_channel, db_user, redemption_data)
        except Exception as ex:
            self.logger.exception(ex)

    async def sync_event(self, msg):
        self.logger.info('Received sync event: {}'.format(msg))

        channel_id = None
        for channel in self.custom_working_channels:
            if channel.user_id == msg['user_id']:
                channel_id = channel.channel_id
                break

        if channel_id is None:
            self.logger.info('Skipping sync because did not find channel by user id {}'.format(msg['user_id']))
            return

        if msg['topic'] == 'twitch_command':
            await self.bot_cp.update(channel_id)
        if msg['topic'] == 'twitch_channel':
            pass  # TODO: channel processor with join/leave mechanics
        if msg['topic'] == 'twitch_notice':
            await self.bot_np.update(channel_id)
        if msg['topic'] == 'twitch_point_reward':
            await self.bot_pp.update(channel_id)
