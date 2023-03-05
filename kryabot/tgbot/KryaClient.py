from aiohttp import ClientResponseError
from telethon import TelegramClient
from telethon.errors import UserNotParticipantError, InviteHashInvalidError, InviteHashExpiredError
from telethon.extensions import html
from telethon.tl import functions
from telethon.tl.functions.channels import LeaveChannelRequest, EditBannedRequest, GetParticipantRequest, \
    GetFullChannelRequest
from telethon.tl.types import PeerUser, PeerChannel, ChatInviteAlready, ChatInvite, ChatBannedRights, ChannelParticipantsAdmins, InputPeerChannel, \
    DocumentAttributeFilename, PeerChat, Chat, InputChannel, Channel, InputStickerSetShortName
from telethon.tl.functions.messages import ImportChatInviteRequest, GetStickerSetRequest, \
    CheckChatInviteRequest, ExportChatInviteRequest
import os
import asyncio
import traceback
from datetime import datetime, date, timedelta

from telethon.utils import get_peer_id

from api.twitchv5.exception import ExpiredAuthToken
from models.dao.BotTask import BotTask, TaskType
from models.dao.TwitchMessage import TwitchMessage
from object.BotConfig import BotConfig
from object.Database import Database
from object.ApiHelper import ApiHelper
from object.Pinger import Pinger
from object.RedisHelper import RedisHelper
from object.System import System
from object.Translator import Translator
from scheduler.scheduler import Scheduler
from tgbot.Moderation import Moderation
import tgbot.events.handlers as krya_events
from tgbot.events.utils import is_valid_channel
from tgbot.events.global_events.GlobalEventFactory import GlobalEventFactory

from utils.formatting import format_html_user_mention
from utils.decorators.exception import log_exception_ignore, log_exception
from utils.value_check import avoid_none, map_kick_setting
from utils.array import split_array_into_parts, get_first
from utils.twitch import refresh_channel_token, get_active_oauth_data
from tgbot.commands.commandbuilder import update_command_list
from utils.constants import TG_GROUP_MONITORING_ID, TG_SUPER_ADMINS, TG_TEST_GROUP_ID
from utils.date_diff import get_datetime_diff_text
from utils import redis_key

global_logger = None
reporter = None
redis_client = None
super_admins = TG_SUPER_ADMINS


def _get_logger():
    # returns actual logger object
    return global_logger


def _get_reporter():
    # returns callable function
    return reporter


class KryaClient(TelegramClient):
    def __init__(self, loop=None, logger=None):
        self.logger = logger
        self.cfg = BotConfig.get_instance()
        self.db = Database.get_instance()
        self.api = ApiHelper.get_instance()
        self.translator = Translator.getInstance()
        self.moderation = None
        self.moderation_queue = asyncio.Queue()
        self.me = None
        self.banned_media = None
        self.participant_cache = []
        self.in_refresh: bool = False

        # Path to session file
        path = os.getenv('SECRET_DIR')
        if path is None:
            path = ''

        super().__init__(path + 'session_name',
                         api_id=self.cfg.getTelegramConfig()['API_ID'],
                         api_hash=self.cfg.getTelegramConfig()['API_HASH'],
                         base_logger=self.logger,
                         connection_retries=100000000)

        self._parse_mode = html

        self.add_event_handler(krya_events.event_private_message)
        self.add_event_handler(krya_events.event_group_message)
        self.add_event_handler(krya_events.event_group_message_edit)
        self.add_event_handler(krya_events.event_group_message_command)
        self.add_event_handler(krya_events.event_chat_action)
        self.add_event_handler(krya_events.event_monitoring_message)
        self.add_event_handler(krya_events.event_group_migrate)

        # For decorators
        global global_logger
        global reporter
        global redis_client

        redis_client = self.db.redis
        global_logger = logger
        reporter = self.exception_reporter
        self.translator.setLogger(self.logger)

    async def start_bot(self):
        await self.update_data()
        self.loop.create_task(Pinger(System.KRYABOT_TELEGRAM, self.logger, self.db.redis).run_task())
        self.loop.create_task(self.db.redis.start_listener(self.redis_subscribe))
        self.loop.create_task(self.bot_task_processor())

        GlobalEventFactory.start_all(self)

        await self.start()
        self.me = await self.get_me()
        await self.get_dialogs()

        await self.report_to_monitoring('[Main] KryaBot for Telegram has started. @Kuroskas')
        await self.report_to_monitoring('/ping')

        # Disabled catch up because it duplicates last actions on some chats
        #await self.catch_up()

        self.logger.info('Updating command list')
        self.loop.create_task(update_command_list(self))
        self.loop.create_task(self.on_remote_request())

    # List of subscribes executed during initialization
    async def redis_subscribe(self):
        await self.db.redis.subscribe_event(redis_key.get_streams_forward_data(), self.on_stream_update)

    async def init_moderation(self, channel_id=None):
        words = await self.db.getTgWords()
        if self.moderation is None:
            self.moderation = Moderation(self.logger, self.moderation_queue, self, cfg=self.cfg.getRedisConfig())

        await self.moderation.setWordList(words)

    async def init_translation(self):
        self.translator.push(await self.db.getTranslations())

    async def init_banned_media(self, channel_id=None):
        self.banned_media = await self.db.getBannedMedia()

    async def init_special_rights(self, channel_id=None):
        # Added to cache
        await self.db.get_all_tg_chat_special_rights(channel_id=channel_id)

    async def init_channels(self, channel_id=None):
        # Added to cache
        await self.db.get_auth_subchats()

    async def init_awards(self, channel_id, user_id):
        # Renew cache
        await self.db.getChannelTgAwards(channel_id, user_id, skip_cache=True)

    async def update_data(self):
        self.logger.debug('Updating data')

        await self.init_channels()
        await self.init_special_rights()
        await self.init_banned_media()
        await self.init_translation()
        await self.init_moderation()
        await self.db.get_global_events()

    async def get_auth_channel(self, tg_chat_id):
        return await self.db.get_auth_subchat(tg_chat_id)

    async def get_all_auth_channels(self):
        return await self.db.get_auth_subchats()

    # TODO: exception traceback
    async def report_exception(self, exception, info=''):
        await self.report_to_monitoring('{}\n{}'.format(info, str(exception)))

    async def exception_reporter(self, err, info):
        await self.report_to_monitoring(message='Error: {}: {}\n\n{}\n\n<pre>{}</pre>'.format(type(err).__name__, err, info, ''.join(traceback.format_tb(err.__traceback__))), avoid_err=True)

    async def report_to_monitoring(self, message, avoid_err=False):
        # avoid_err used to avoid infinitive loop on reporting fail
        try:
            await self.send_message(TG_GROUP_MONITORING_ID, message)
        except Exception as err:
            if avoid_err is False:
                raise err

    @log_exception_ignore(log=_get_logger, reporter=_get_reporter)
    async def restrict_user(self, channel_entity, user_entity, rights):
        await self(EditBannedRequest(channel_entity, user_entity, rights))

    @log_exception_ignore(log=_get_logger, reporter=_get_reporter)
    async def kick_user_from_channel(self, tg_chat_id, tg_user_id, ban_time):
        if not isinstance(tg_chat_id, PeerChannel):
            tg_chat_id = PeerChannel(int(tg_chat_id))

        if not isinstance(tg_user_id, PeerUser):
            tg_user_id = PeerUser(int(tg_user_id))

        await self.db.update_tg_stats_kick(tg_chat_id)

        chat_entity = await self.get_entity(tg_chat_id)
        user_entity = await self.get_entity(tg_user_id)
        await self.kick_user(chat_entity, user_entity, ban_time)

    @log_exception_ignore(log=_get_logger, reporter=_get_reporter)
    async def kick_user(self, channel_entity, user_entity, ban_time):
        # print('kicking')
        # print(user_entity.stringify())
        rights = ChatBannedRights(
            until_date=timedelta(seconds=ban_time),
            view_messages=True)

        await self.restrict_user(channel_entity, user_entity, rights)

    @log_exception_ignore(log=_get_logger, reporter=_get_reporter)
    async def mute_user(self, channel_entity, user_entity, ban_time):
        try:
            rights = ChatBannedRights(
                until_date=timedelta(seconds=ban_time),
                view_messages=None,
                send_messages=True,
                send_media=True,
                send_stickers=True,
                send_gifs=True,
                send_games=True,
                send_inline=True,
                embed_links=True)
            await self.restrict_user(channel_entity, user_entity, rights)
        except Exception as err:
            await self.exception_reporter(err, 'Moderation mute:')

    async def run_channel_refresh_remote(self, kb_user_id, is_kick, params):
        chat_id = await self.db.getTgChatIdByUserId(kb_user_id)

        if chat_id is None or len(chat_id) == 0 or chat_id[0]['tg_chat_id'] is None:
            self.logger.error('Exiting remote refresh because chat ID was not found for user ID {}'.format(kb_user_id))
            return

        channel = await self.db.get_auth_subchat(tg_chat_id=chat_id[0]['tg_chat_id'], skip_cache=True)
        if len(channel) == 0:
            channel = None
        else:
            channel = channel[0]

        if not is_valid_channel(channel):
            return

        if channel['refresh_status'] == 'WAIT':
            self.logger.info('Skipping channel {} refresh because current status is WAIT'.format(channel['tg_chat_id']))
            return

        await self.run_channel_refresh_new(channel, is_kick, params)

    async def run_channel_refresh_new(self, channel, kick, params, silent=False, dry_run=False):
        self.logger.info('Task: Refresh group members Channel: {}'.format(channel['channel_name']))
        self.logger.info('Kick: {} params: {}'.format(kick, params))
        report = '[Task]\nType: Refresh group members\nChannel: {}'.format(channel['channel_name'])
        report += '\nAuto-kick: {}'.format(kick)

        channel_entity = await self.get_entity(PeerChannel(channel['tg_chat_id']))

        data = await self.get_group_participant_full_data(channel, need_follows=channel['join_follower_only'] == 1, kick_not_verified=False, kick_deleted=False)
        allowed_to_kick = False if dry_run or silent else channel['auto_kick']
        if len(data['users']) == 0:
            await self.report_to_monitoring(report + '\nStatus: Failed\nReason: Empty telegram chat')
            return

        # Force stop if want to kick >90% users
        kick_ratio = data['summary']['subs'] / (data['summary']['total'] - data['summary']['bots'])
        if kick and kick_ratio < 0.1:
            await self.report_to_monitoring('Force stopping mass-kick for channel {} because kick ratio is {}'.format(channel['channel_name'], kick_ratio))
            return

        kickNonVerified = False
        kickNonSub = False
        kickDeleted = False
        kickNonFollower = False

        kicked_total = 0
        kicked_not_verified = 0
        kicked_deleted = 0
        kicked_blacklist = 0
        kicked_non_sub = 0
        kicked_non_follow = 0

        max_sanity_check = 5

        if kick:
            await self.send_message(channel['tg_chat_id'], self.translator.getLangTranslation(channel['bot_lang'], 'MASS_KICK_START'), parse_mode='html')
            await self.send_krya_mass_kill_sticker(channel['tg_chat_id'])
            report += '\n\nKick parameters:'
            for setting in params:
                if setting['key'] == 'not_verified':
                    kickNonVerified = setting['enabled']
                if setting['key'] == 'not_sub':
                    kickNonSub = setting['enabled']
                if setting['key'] == 'not_active':
                    kickDeleted = setting['enabled']
                if setting['key'] == 'not_follower':
                    kickNonFollower = setting['enabled']
                report += '\n' + await map_kick_setting(setting['key']) + str(setting['enabled'])
            report += '\n'

        error_message = ''

        if not dry_run:
            await self.db.startTgMemberRefresh(channel['tg_chat_id'])

        kick_array = []
        async with self.action(channel['tg_chat_id'], 'game'):
            for user in data['users']:
                if user['tg'].bot:
                    continue

                sanity_check = 0

                while True:
                    if sanity_check > max_sanity_check:
                        break

                    user_string = await avoid_none(user['tg'].first_name) \
                                  + ' ' + await avoid_none(user['tg'].last_name) \
                                  + ' ' + await avoid_none(user['tg'].username)
                    try:
                        if kickDeleted and user['tg'].deleted is True:
                            kicked_total += 1
                            kicked_deleted += 1
                            kick_array.append('{} (Deleted account)'.format(user['tg'].id))
                            self.logger.info(('[Deleted] Kicking: ' + user_string).encode())
                            if allowed_to_kick:
                                await self.kick_user(channel_entity, user['tg'], channel['ban_time'])
                            break

                        if kick and user['is_blacklist'] and not user['tg_admin']:
                            kicked_total += 1
                            kicked_blacklist += 1
                            kick_array.append('{} (Blacklisted account)'.format(user_string))
                            self.logger.info(('[Blacklisted] Kicking: ' + user_string).encode())
                            if allowed_to_kick:
                                await self.kick_user(channel_entity, user['tg'], channel['ban_time'])
                            break

                        # Not verified
                        if kickNonVerified and not user['kb'] and not user['tg_admin']:
                            kicked_total += 1
                            kicked_not_verified += 1
                            kick_array.append('{} (Not verified)'.format(user_string))
                            self.logger.info(('[Not-verified] Kicking: ' + user_string).encode())
                            if allowed_to_kick:
                                await self.kick_user(channel_entity, user['tg'], channel['ban_time'])
                            break

                        sub_tier = 'No'
                        if user['kb']:
                            # Check follow
                            if channel['join_follower_only'] and kickNonFollower and not user['is_whitelist'] and not user['tg_admin'] and not user['twitch']['follow']:
                                kicked_total += 1
                                kicked_non_follow += 1
                                kick_array.append('{} (Not follower: {})'.format(user_string, user['kb']['name']))
                                self.logger.info(('[Non-follower] Kicking: ' + user_string).encode())
                                if allowed_to_kick:
                                    await self.kick_user(channel_entity, user['tg'], channel['ban_time'])
                                break

                            if user['twitch']['sub']:
                                sub_tier = user['twitch']['sub']['tier']

                            # Check sub
                            if channel['join_sub_only'] and kickNonSub and not user['is_whitelist'] and not user['tg_admin'] and not user['twitch']['sub']:
                                kicked_total += 1
                                kicked_non_sub += 1
                                kick_array.append('{} (Not subscriber: {})'.format(user_string, user['kb']['name']))
                                self.logger.info(('[Non-sub] Kicking: ' + user_string).encode())
                                if allowed_to_kick:
                                    await self.kick_user(channel_entity, user['tg'], channel['ban_time'])
                                break

                        await self.db.saveTgMember(channel['tg_chat_id'],
                                                   user['tg'].id,
                                                   await avoid_none(user['tg'].first_name),
                                                   await avoid_none(user['tg'].last_name),
                                                   await avoid_none(user['tg'].username),
                                                   sub_tier)
                    except Exception as ex:
                        self.logger.exception(ex)
                        await self.report_exception(exception=ex, info='User: {}'.format(user_string))
                        error_message = str(ex)
                        if 'EditBannedRequest' in error_message:
                            if 'A wait of' in error_message:
                                try:
                                    wlist = error_message.split(' ')
                                    wait_time = int(wlist[3])
                                    wait_time += 10
                                except:
                                    wait_time = 600
                                await self.send_message(channel['tg_chat_id'], self.translator.getLangTranslation(channel['bot_lang'], 'MASS_KICK_PAUSE').format(wt=wait_time))
                                await asyncio.sleep(wait_time)
                                await self.send_message(channel['tg_chat_id'], self.translator.getLangTranslation(channel['bot_lang'], 'MASS_KICK_RESUME'))
                            if 'not an admin' in error_message:
                                break
                        continue

                    # Everything is ok, exit whileTrue
                    break

                if sanity_check > max_sanity_check:
                    if not silent:
                        await self.send_message(channel['tg_chat_id'], self.translator.getLangTranslation(channel['bot_lang'], 'MASS_KICK_SANITY_STOP'))
                    break

        self.logger.debug('Mass kick loop finished')
        if not dry_run:
            await self.db.finishTgMemberRefresh(channel['tg_chat_id'], error_message)

        if not silent:
            await self.report_to_monitoring(report + '\nStatus: Done\nTotal members: ' + str(data['summary']['total']) + '\nVerified: ' + str(data['summary']['verified']) + '\nSubscribers: ' + str(data['summary']['subs']))

        if kick and not silent:
            kick_report = self.translator.getLangTranslation(channel['bot_lang'], 'MASS_KICK_FINISH')
            if kicked_total > 0:
                kick_report += '\n\n<b>⚠️{}: {}</b>\n'.format(self.translator.getLangTranslation(channel['bot_lang'], 'MASS_KICK_KICKED_TOTAL'), kicked_total)
                if kicked_deleted > 0:
                    kick_report += '\n➖ {} {}'.format(self.translator.getLangTranslation(channel['bot_lang'], 'MASS_KICK_KICKED_DELETED'), kicked_deleted)
                if kicked_blacklist > 0:
                    kick_report += '\n➖ {}: {}'.format(self.translator.getLangTranslation(channel['bot_lang'], 'MASS_KICK_KICKED_BANNED'), kicked_blacklist)
                if kicked_not_verified > 0:
                    kick_report += '\n➖ {}: {}'.format(self.translator.getLangTranslation(channel['bot_lang'], 'MASS_KICK_KICKED_NOT_VERIFIED'), kicked_not_verified)
                if kicked_non_follow > 0:
                    kick_report += '\n➖ {}: {}'.format(self.translator.getLangTranslation(channel['bot_lang'], 'MASS_KICK_KICKED_NOT_FOLLOWER'), kicked_non_follow)
                if kicked_non_sub > 0:
                    kick_report += '\n➖ {}: {}'.format(self.translator.getLangTranslation(channel['bot_lang'], 'MASS_KICK_KICKED_NOT_SUB'), kicked_non_sub)

                await self.send_file(channel['tg_chat_id'], file='\n'.join(kick_array).encode(), caption=kick_report, attributes=[DocumentAttributeFilename('MassKickReport.txt')])
            else:
                await self.send_message(channel['tg_chat_id'], kick_report + '\n\n🙄 ' + self.translator.getLangTranslation(channel['bot_lang'], 'MASS_KICK_KICKED_NOTHING'))

            if kick_array:
                await self.send_file(TG_GROUP_MONITORING_ID, file='\n'.join(kick_array).encode(), caption=kick_report, attributes=[DocumentAttributeFilename('{}_report.txt'.format(channel['channel_name']))])

        if not dry_run:
            await self.db.get_auth_subchat(channel['tg_chat_id'], skip_cache=True)
            await self.update_data()

    @log_exception_ignore(log=_get_logger, reporter=_get_reporter)
    async def is_whitelisted(self, kb_user_id, tg_user_id, channel)->bool:
        return bool(await self.has_special_right(kb_user_id, tg_user_id, channel, 'WHITELIST'))

    @log_exception_ignore(log=_get_logger, reporter=_get_reporter)
    async def is_blacklisted(self, kb_user_id, tg_user_id, channel)->bool:
        return bool(await self.has_special_right(kb_user_id, tg_user_id, channel, 'BLACKLIST'))

    @log_exception_ignore(log=_get_logger, reporter=_get_reporter)
    async def is_chatsudo(self, kb_user_id, tg_user_id, channel)->bool:
        return bool(await self.has_special_right(kb_user_id, tg_user_id, channel, 'SUDO'))

    @log_exception_ignore(log=_get_logger, reporter=_get_reporter)
    async def has_special_right(self, kb_user_id, tg_user_id, channel, right_type)->bool:
        try:
            special_rights = await self.db.get_all_tg_chat_special_rights(channel['channel_id'])
        except Exception as err:
            await self.exception_reporter(err, 'has_special_right')
            return False

        if special_rights is None:
            return False

        # By user ID (new)
        if kb_user_id is not None and kb_user_id > 0:
            for right in special_rights:
                if right['user_id'] == kb_user_id and right['right_type'] == right_type:
                    return True

        # By telegram ID (legacy)
        for right in special_rights:
            if right['tg_user_id'] == tg_user_id and right['right_type'] == right_type and (right['user_id'] is None or right['user_id'] == 0):
                return True

        return False

    @log_exception_ignore(log=_get_logger, reporter=_get_reporter)
    async def has_special_rights(self, kb_user_id, tg_user_id, channel):
        special_rights = await self.db.get_all_tg_chat_special_rights(channel['channel_id'])

        has_whitelist = False
        has_blacklist = False
        blacklist_comment = None

        if special_rights is None:
            return has_whitelist, has_blacklist, blacklist_comment

        # By user ID (new)
        if kb_user_id is not None and kb_user_id > 0:
            for right in special_rights:
                if right['user_id'] == kb_user_id and right['right_type'] == 'WHITELIST':
                    has_whitelist = True
                if right['user_id'] == kb_user_id and right['right_type'] == 'BLACKLIST':
                    has_blacklist = True
                    blacklist_comment = right['comment']

        # By telegram ID (legacy)
        for right in special_rights:
            if right['tg_user_id'] == tg_user_id and right['right_type'] == 'WHITELIST' and (right['user_id'] is None or right['user_id'] == 0):
                has_whitelist = True
            if right['tg_user_id'] == tg_user_id and right['right_type'] == 'BLACKLIST' and (right['user_id'] is None or right['user_id'] == 0):
                has_blacklist = True
                blacklist_comment = right['comment']

        return has_whitelist, has_blacklist, blacklist_comment

    async def run_user_report(self, channel, manual=False):
        channel = await refresh_channel_token(channel=channel, force_refresh=True)
        data = await self.get_group_participant_full_data(channel, need_follows=channel['join_follower_only'] == 1, kick_not_verified=not manual and channel['auto_kick'] == 1, kick_deleted=channel['auto_kick'] == 1)
        lang = channel['bot_lang']
        summary = data['summary']
        self.logger.info("Summary for channel {}: {}".format(channel['channel_id'], summary))

        if manual is True or channel['show_report'] == 1:
            async with self.action(channel['tg_chat_id'], 'document'):
                report = self.translator.getLangTranslation(lang, 'UR_TITLE')
                report += '\n\n{label}: {val}'.format(val=summary['total'], label=self.translator.getLangTranslation(lang, 'UR_TOTAL'))
                report += '\n{label}: {val}'.format(val=summary['subs'], label=self.translator.getLangTranslation(lang, 'UR_SUBS'))
                report += '\n{label}: {val}'.format(val=(summary['non_subs']), label=self.translator.getLangTranslation(lang, 'UR_NON_SUBS'))
                if summary['followers'] > 0:
                    report += '\n{label}: {val}'.format(val=summary['followers'], label=self.translator.getLangTranslation(lang, 'UR_FOLLOWS'))
                if summary['non_verified'] > 0:
                    report += '\n{label}: {val}'.format(val=summary['non_verified'], label=self.translator.getLangTranslation(lang, 'UR_NON_VERIFIED'))
                if summary['deleted'] > 0:
                    report += '\n{label}: {val}'.format(val=summary['deleted'], label=self.translator.getLangTranslation(lang, 'UR_TG_DELETED'))
                if summary['bots'] > 0:
                    report += '\n{label}: {val}'.format(val=summary['bots'], label=self.translator.getLangTranslation(lang, 'UR_BOTS'))
                if summary['kicked'] > 0:
                    report += '\n{label}: {val}'.format(val=summary['kicked'], label=self.translator.getLangTranslation(lang, 'UR_KICKED'))

                if summary['whitelists'] > 0:
                    report += '\n{label}: {val}'.format(val=summary['whitelists'], label=self.translator.getLangTranslation(lang, 'UR_VIP'))
                if summary['blacklists'] > 0:
                    report += '\n{label}: {val}'.format(val=summary['blacklists'], label=self.translator.getLangTranslation(lang, 'UR_BANNED'))
                if summary['sudos'] > 0:
                    report += '\n{label}: {val}'.format(val=summary['sudos'], label=self.translator.getLangTranslation(lang, 'UR_SUDO'))

                if summary['is_authorised'] == 0:
                    report += '\n\n<b>{}</b>'.format(self.translator.getLangTranslation(lang, 'UR_SUB_CHECK_FAILED'))

                if summary['next_mk'] and summary['next_mk'] > datetime.now():
                    formatted = await get_datetime_diff_text(summary['next_mk'], datetime.now())
                    report += '\n\n{} {}!'.format(self.translator.getLangTranslation(lang, 'CMD_NEXT_IN'), formatted)

                report += '\n\n'
                report += self.translator.getLangTranslation(lang, 'UR_FOOTER')
                await self.send_message(channel['tg_chat_id'], report, parse_mode='html')

        if manual is False:
            when_now = date.today()
            when_y = when_now - timedelta(days=1)

            # Update yesterday stats in DB
            data_chat = await self.db.get_tg_stats_from_cache(tg_chat_id=channel['tg_chat_id'], dt=when_y)

            await self.db.save_tg_stats_msg(channel_id=channel['channel_id'], when_dt=when_y, counter=data_chat['message'])
            await self.db.save_tg_stats_join(channel_id=channel['channel_id'], when_dt=when_y, counter=data_chat['join'])
            await self.db.save_tg_stats_kick(channel_id=channel['channel_id'], when_dt=when_y, counter=data_chat['kick'])
            await self.db.save_tg_stats_sub(channel_id=channel['channel_id'], when_dt=when_now, counter=summary['subs'])
            await self.db.save_tg_stats_nonsub(channel_id=channel['channel_id'], when_dt=when_now, counter=summary['non_subs'])
            await self.db.save_tg_stats_wls(channel_id=channel['channel_id'], when_dt=when_now, counter=summary['whitelists'])
            await self.db.save_tg_stats_bls(channel_id=channel['channel_id'], when_dt=when_now, counter=summary['blacklists'])
            await self.db.save_tg_stats_bots(channel_id=channel['channel_id'], when_dt=when_now, counter=summary['bots'])
            await self.db.save_tg_stats_total(channel_id=channel['channel_id'], when_dt=when_now, counter=summary['total'])

    async def get_sticker_set(self, pack_name):
        return await self(GetStickerSetRequest(stickerset=InputStickerSetShortName(pack_name), hash=0))

    @log_exception_ignore(log=_get_logger, reporter=_get_reporter)
    async def send_krya_sticker(self, chat_id, emo):
        kryabot_stickers = await self.get_sticker_set('KryaBot')
        for sticker in kryabot_stickers.packs:
            if sticker.emoticon == emo:
                for pack in kryabot_stickers.documents:
                    if sticker.documents[0] == pack.id:
                        await self.send_file(chat_id, pack)

    @log_exception_ignore(log=_get_logger, reporter=_get_reporter)
    async def join_channel(self, kb_user_id):
        report = '[Task]\nType: Channel join\nUser ID: ' + str(kb_user_id)
        chat_data = await self.db.getSubchatByUserId(kb_user_id)
        if chat_data is None or len(chat_data) == 0:
            await self.report_to_monitoring(report + " \n\nFailed, no chat found by user id!")
            return

        chat_data = chat_data[0]
        report += "\nChannel ID: " + str(chat_data['channel_id'])

        if chat_data['tg_chat_id'] == 0 and (chat_data['join_link'] is None or chat_data['join_link'] == ""):
            # Skip and do not report it
            return
        elif chat_data['tg_chat_id'] > 0 and (chat_data['join_link'] is None or chat_data['join_link'] == ""):
            # Removed invite link, need to leave
            await self.db.updateSubchatAfterJoin(chat_data['channel_subchat_id'], 0, '', '')
            report += '\nRemoving bot from telegram group {}'.format(chat_data['tg_chat_id'])
            try:
                old_entity = await self.get_input_entity(PeerChannel(int(chat_data['tg_chat_id'])))
                await self(LeaveChannelRequest(old_entity))
            except Exception as ex:
                report += '\nError during channel leave: {}'.format(ex)
        else:
            try:
                invite_hash = chat_data['join_link']
                if 't.me' in invite_hash:
                    invite_hash = invite_hash.split('/')[-1]

                if invite_hash.startswith('+'):
                    invite_hash = invite_hash[1:]

                chat_check = await self(CheckChatInviteRequest(invite_hash))
                # Existing channel
                if type(chat_check) is ChatInviteAlready:
                    if chat_check.chat.id == chat_data['tg_chat_id']:
                        await self.db.updateSubchatAfterJoin(chat_data['channel_subchat_id'], chat_check.chat.id, chat_check.chat.title.encode(), chat_data['join_link'])
                    else:
                        # Tried to join other user channel, delete link and keep old ID
                        await self.db.updateSubchatAfterJoin(chat_data['channel_subchat_id'], chat_data['tg_chat_id'], chat_data['tg_chat_name'], '')
                # New channel provided
                elif type(chat_check) is ChatInvite:
                    new_chat = await self(ImportChatInviteRequest(invite_hash))

                    if chat_data['tg_chat_id'] > 0:
                        # Leave previous channel
                        try:
                            old_entity = await self.get_input_entity(PeerChannel(int(chat_data['tg_chat_id'])))
                            await self(LeaveChannelRequest(old_entity))
                        except Exception as e:
                            await self.report_exception(e, 'Channel leave from {} ({})'.format(chat_data['tg_chat_id'], chat_data['tg_chat_name']))
                            pass
                    else:
                        # First time join
                        pass
                    await self.send_message(new_chat.chats[0].id, message='HoHoHo')
                    await self.db.updateSubchatAfterJoin(chat_data['channel_subchat_id'], new_chat.chats[0].id, new_chat.chats[0].title.encode(), chat_data['join_link'])
                else:
                    # TODO: ?
                    pass

                await self.update_data()
            except Exception as e:
                self.logger.info(str(e))
                report += '\nJoin with error: ' + str(e)

        await self.report_to_monitoring(report + '\nStatus: Done')

    @log_exception_ignore(log=_get_logger, reporter=_get_reporter)
    async def is_media_banned(self, channel_id, media_id, media_type):
        if media_type is None or media_type == '':
            return False

        for banned in self.banned_media:
            if banned['channel_id'] == channel_id and banned['media_id'] == str(media_id) and banned['media_type'] == media_type:
                return True

        return False

    async def send_krya_guard_sticker(self, chat_id):
        await self.send_krya_sticker(chat_id, '⚔')

    async def send_krya_kill_sticker(self, chat_id):
        await self.send_krya_sticker(chat_id, '🗡')

    async def send_krya_love_sticker(self, chat_id):
        await self.send_krya_sticker(chat_id, '😍')

    async def send_krya_mass_kill_sticker(self, chat_id):
        await self.send_krya_sticker(chat_id, '👿')

    def get_translation(self, lang, key):
        return self.translator.getLangTranslation(lang, key)

    async def task_oauth_refresher(self):
        await asyncio.sleep(10)

        try:
            auths = await self.db.getBotAuths()

            for auth in auths:
                new_auth = await get_active_oauth_data(auth['user_id'], sec_diff=(900 + 60))
        except Exception as e:
            self.logger.error(str(e))
            await self.exception_reporter(e, 'In task_oauth_refresher')

    async def twitch_event_unsubscribe(self, event_id):
        twitch_event = await self.db.getTwitchEventByEventId(event_id)
        if twitch_event is None or len(twitch_event) == 0:
            self.logger.info('Received unsubscribe event ID {}, but event not found'.format(event_id))
            return

        twitch_event = twitch_event[0]

        tg_chat = await self.db.getTgChatIdByChannelId(twitch_event['channel_id'])
        if tg_chat is None or len(tg_chat) == 0:
            self.logger.info('Received unsubscribe event ID {}, but subchat was not found for it.'.format(event_id))
            return
        tg_chat = tg_chat[0]

        target_user = await self.db.getResponseByUserId(twitch_event['user_id'])
        if target_user is None or len(target_user) == 0:
            self.logger.info('Received unsubscribe event ID {}, but user does not have any telegram link'.format(event_id))
            return
        target_user = target_user[0]

        participant = await self.find_participant(int(tg_chat['tg_chat_id']), int(target_user['tg_id']))
        if participant is None:
            self.logger.info(
                'Received unsubscribe event ID {}, but user {} is not participant of chat {}'.format(event_id, target_user['tg_id'], tg_chat['tg_chat_id']))
            return

        participant = await self.get_entity(int(target_user['tg_id']))
        chat = await self.db.get_auth_subchat(tg_chat_id=tg_chat['tg_chat_id'])
        chat_entity = await self.get_entity(PeerChannel(int(tg_chat['tg_chat_id'])))
        formatted_mention = await format_html_user_mention(participant)
        await self.report_to_monitoring(message='[Unsubscribe] User {} in chat {}\nEvent ID: {}'.format(formatted_mention, chat['channel_name'], event_id))

        if chat['on_refund'] == 0:
            return

        if chat['on_refund'] >= 1:
            text = '{} {} 😨'.format(formatted_mention,self.translator.getLangTranslation(chat['bot_lang'], 'USER_UNSUBSCRIBE_EVENT'))
            await self.send_message(tg_chat['tg_chat_id'], message=text)

        ban_time = chat['ban_time']
        if chat['on_refund'] == 3:
            ban_time = 86400 * 7
        if chat['on_refund'] == 4:
            ban_time = 86400 * 30

        if chat['on_refund'] == 5:
            await self.db.addUserToBlacklist(chat['channel_id'],
                                             twitch_event['user_id'],
                                             participant.id,
                                             await avoid_none(participant.first_name),
                                             await avoid_none(participant.last_name),
                                             await avoid_none(participant.username),
                                             self.me.id,
                                             'Twitch Sub refund')
            await self.init_special_rights(chat['channel_id'])

        if chat['on_refund'] >= 2:
            await self.kick_user(chat_entity, participant, ban_time)
            await self.send_krya_kill_sticker(chat_id=chat['tg_chat_id'])

    async def find_participant(self, tg_chat_id, tg_user_id):
        self.logger.debug('Searching for user {} in chat {}'.format(tg_user_id, tg_chat_id))
        try:
            channel_entity = await self.get_input_entity(int(tg_chat_id))
            user_entity = await self.get_input_entity(int(tg_user_id))
            return await self(GetParticipantRequest(channel=channel_entity, participant=user_entity))
        except UserNotParticipantError:
            return None
        except ValueError:
            return None

    async def task_global_user_report(self):
        await self.update_data()
        for channel in (await self.db.get_auth_subchats()):
            if channel['tg_chat_id'] == 0:
                continue

            try:
                await self.report_to_monitoring('[Daily] Starting daily user report for channel {}'.format(channel['channel_name']), avoid_err=True)
                await self.run_user_report(channel=channel)
            except Exception as err:
                await self.exception_reporter(err=err, info='Error during daily user report for channel {}'.format(channel['channel_name']))

    async def get_group_admins_cache(self, chat_entity, skip_cache=False):
        # We work only channels, currently do not need to support chats
        if not skip_cache:
            if isinstance(chat_entity, InputPeerChannel):
                for data in self.participant_cache:
                    # cache expires in 1 hour
                    if data['id'] == chat_entity.channel_id:
                        if data['ts'] + timedelta(hours=1) > datetime.now():
                            return data['list']
                        else:
                            self.participant_cache.remove(data)

        # skip, expired, new
        obj = {}
        obj['id'] = chat_entity.channel_id
        obj['ts'] = datetime.now()
        obj['list'] = []

        async for user in self.iter_participants(chat_entity, filter=ChannelParticipantsAdmins):
            obj['list'].append(user)

        self.participant_cache.append(obj)
        return obj['list']

    async def mute_from_twitch(self, from_user_id, target_user_id, channel_id, duration)->bool:
        chat = await self.db.getTgChatIdByChannelId(channel_id)
        from_user = await self.db.getUserById(from_user_id)

        return True

    async def message_from_twitch(self, from_user_id, channel_id, message)->bool:
        return True

    async def on_stream_update(self, data):
        twitch_id = data['channel_id']
        twitch_name = data['channel_name']
        channel = None
        channels = await self.db.get_auth_subchats()
        for ch in channels:
            if int(ch['tw_id']) == int(twitch_id):
                channel = ch

        if channel is None:
            self.logger.info('Skip. User {} has no telegram group for notification'.format(twitch_name))
            return

        if channel['tg_chat_id'] == 0:
            return

        if channel['on_stream'] < 1 or data['start'] != 1:
            return

        custom_url = data['img_url']
        twitchurl = '<a href="https://twitch.tv/{ch}">{ch}</a>'.format(ch=twitch_name)
        notification_text = self.translator.getLangTranslation(channel['bot_lang'], 'NOTIFICATION_START').format(twitchurl=twitchurl, ttl=data['title'])
        nofitication_message = await self.send_file(channel['tg_chat_id'], caption=notification_text, parse_mode="html", file=custom_url, allow_cache=False)

        if channel['on_stream'] == 2:
            await nofitication_message.pin(notify=True)

    async def handle_person_unlink(self, unlink_tg_id, unlink_tw_id, unlink_kb_id, body):
        check_channels = [ch for ch in await self.db.get_auth_subchats() if ch['auto_kick']]

        self.logger.info('Linked TG account. ID: {}, TG: {}'.format(unlink_kb_id, unlink_tg_id))
        removed_from = ''
        err = None
        try:
            for ch in check_channels:
                if ch['tg_chat_id'] == 0:
                    continue

                try:
                    if await self.find_participant(ch['tg_chat_id'], unlink_tg_id):
                        await self.kick_user_from_channel(ch['tg_chat_id'], unlink_tg_id, ch['ban_time'])
                        self.logger.info('Removed user {} from chat {}'.format(unlink_kb_id, ch['tg_chat_id']))
                        removed_from += ' ' + str(ch['tg_chat_id'])
                except Exception as e:
                    await asyncio.sleep(1)
                    self.logger.exception(e)

            # Remove cached data
            await self.db.getUserRecordByTwitchId(unlink_tw_id, skip_cache=True)
            await self.db.getUserByTgChatId(unlink_tg_id, skip_cache=True)
            await self.db.get_all_tg_chat_special_rights()
        except Exception as e2:
            err = e2
            self.logger.error('Exception during unlink of user {}'.format(str(unlink_kb_id)))
            self.logger.exception(e2)

        if len(removed_from) > 0:
            removed_from = 'Removed from: {}'.format(removed_from)

        await self.report_to_monitoring('[Unlinked] {} \n{}'.format(body, str(err) if err is not None else removed_from))

    async def sync_router(self, user_id, topic):
        self.logger.info('Publishing sync topic {} for user {}'.format(topic, user_id))
        channel = await self.db.getChannelByUserId(user_id)
        if channel is None or len(channel) == 0:
            self.logger.error('Skipping sync task because channel record was not found!')
            return

        channel = channel[0]
        if topic in ['twitch_command', 'twitch_channel', 'twitch_notice', 'twitch_point_reward']:
            data = {"user_id": user_id,
                    "topic": topic,
                    "channel": channel}
            await self.db.redis.publish_event(redis_key.get_sync_topic(), data)

        if topic == 'telegram_banned_media':
            await self.init_banned_media(channel['channel_id'])
        if topic == 'telegram_banned_words':
            await self.init_moderation(channel['channel_id'])
        if topic == 'telegram_member_rights':
            await self.init_special_rights(channel['channel_id'])
        if topic == 'telegram_group':
            await self.init_channels(channel['channel_id'])
        if topic == 'telegram_award':
            await self.init_awards(channel['channel_id'], user_id)

    @log_exception_ignore(log=_get_logger)
    async def get_group_member_count(self, tg_group_id: int, skip_cache=False)->int:
        if tg_group_id == TG_TEST_GROUP_ID:
            return 100

        data = None
        if not skip_cache:
            data = await self.db.get_telegram_group_size_from_cache(tg_group_id)

        if data is None:
            data = (await self.get_participants(entity=int(tg_group_id), limit=0)).total
            await self.db.save_telegram_group_size_to_cache(tg_group_id, data)

        return int(data) if data else 0

    @log_exception_ignore(log=_get_logger)
    async def task_check_chat_publicity(self, sleep=60):
        chats = await self.get_all_auth_channels()

        for chat in chats:
            if chat['tg_chat_id'] == 0:
                continue

            await asyncio.sleep(sleep)
            try:
                full_info = await self(GetFullChannelRequest(channel=chat['tg_chat_id']))
                channel = full_info.chats[0]
                if chat['force_pause'] == 0 and full_info.full_chat.linked_chat_id is not None and full_info.full_chat.linked_chat_id > 0:
                    # Linked to channel
                    self.logger.info("Group {} linked to {}".format(chat['tg_chat_id'], full_info.full_chat.linked_chat_id))
                    await self.report_to_monitoring("Force pausing channel {} ({}) because linked to channel {}".format(channel.title, channel.id,full_info.full_chat.linked_chat_id))
                    await self.db.updateChatForcePause(chat['tg_chat_id'], True)
                elif chat['force_pause'] == 0 and channel.username is not None and len(channel.username) > 0:
                    # Public username was given
                    self.logger.info("Group {} has username {}".format(chat['tg_chat_id'], channel.username))
                    await self.report_to_monitoring("Force pausing channel {} ({}) because it has username {}".format(channel.title, channel.id, channel.username))
                    await self.db.updateChatForcePause(chat['tg_chat_id'], True)
                elif chat['force_pause'] == 1 and full_info.full_chat.linked_chat_id is None and channel.username is None:
                    # Link/username was removed
                    self.logger.info("Group {} removing force pause".format(chat['tg_chat_id']))
                    await self.report_to_monitoring("Force un-pausing channel {} ({})".format(channel.title, channel.id))
                    await self.db.updateChatForcePause(chat['tg_chat_id'], False)
                else:
                    self.logger.info('Unhandled publicity check state for group {}: {}, {}'.format(chat['tg_chat_id'], full_info.full_chat.linked_chat_id, channel.username))
            except Exception as ex:
                await self.report_exception(ex, info=chat)

    @log_exception_ignore(log=_get_logger)
    async def task_check_invite_links(self):
        chats = await self.get_all_auth_channels()

        for chat in chats:
            # No subchat
            if chat['tg_chat_id'] == 0 or chat['join_link'] is None or chat['join_link'] == '':
                continue

            await asyncio.sleep(15)
            try:
                try:
                    check = await self(CheckChatInviteRequest(hash=chat['join_link']))
                    continue
                except (InviteHashInvalidError, InviteHashExpiredError):
                    # Expired / invalid
                    new_link = await self(ExportChatInviteRequest(peer=chat['tg_chat_id']))
                    self.logger.info('Generated new invite link: {}'.format(new_link))
                    await self.db.updateInviteLink(chat['tg_chat_id'], new_link=new_link.link)
            except Exception as ex:
                self.logger.exception(ex)
                await self.report_exception(ex, info=chat)

    @log_exception_ignore(log=_get_logger)
    async def task_fix_twitch_ids(self):
        try:
            sql = "select * from user where user.tw_id = 0 and user.name != ''"
            rows = await self.db.do_query(sql, [])
            if rows is None or len(rows) == 0:
                return

            params = [int(user['name']) for user in rows]
            if len(params) == 0:
                return

            parts = split_array_into_parts(params, 100)
            for part in parts:
                self.logger.info('Fixing Twitch ID for users: {}'.format(part))
                users = await self.api.twitch.get_users(usernames=part, skip_cache=True)
                for twitch_user in users['data']:
                    kb_user = next(filter(lambda row: str(row['name']) == str(twitch_user['login']), rows))
                    self.logger.info('Updating Twitch ID for user {} to {}'.format(kb_user['name'], twitch_user['id']))
                    await self.db.updateUserTwitchId(kb_user['user_id'], int(twitch_user['id']))

            rows = await self.db.do_query(sql, [])
            if rows and len(rows) > 0:
                self.logger.info('After fixing Twitch IDs, {} users still not fixed: {}'.format(len(rows), [int(user['user_id']) for user in rows]))
        except Exception as e:
            await self.exception_reporter(e, 'task_fix_twitch_ids')

    @log_exception_ignore(log=_get_logger)
    async def task_fix_twitch_names(self):
        try:
            sql = "select * from user where user.name = ''"
            rows = await self.db.do_query(sql, [])
            if rows is None or len(rows) == 0:
                return

            params = [int(user['tw_id']) for user in rows]
            if len(params) == 0:
                return

            parts = split_array_into_parts(params, 100)
            for part in parts:
                self.logger.info('Fixing Twitch Names for users: {}'.format(part))
                users = await self.api.twitch.get_users(ids=part, skip_cache=True)

                for user in users['data']:
                    kb_user = next(filter(lambda row: int(row['tw_id']) == int(user['id']), rows))
                    self.logger.info('Updating Twitch name for user {} to {}'.format(kb_user['tw_id'], user['login']))
                    await self.db.updateUserTwitchName(kb_user['user_id'], user['login'], user['display_name'], tw_user_id=int(user['id']))

            rows = await self.db.do_query(sql, [])
            if rows and len(rows) > 0:
                self.logger.info('After fixing Twitch names, {} users still not fixed: {}'.format(len(rows), [int(user['user_id']) for user in rows]))
        except Exception as e:
            await self.exception_reporter(e, 'task_fix_twitch_names')

    @log_exception_ignore(log=_get_logger)
    async def task_delete_old_messages(self):
        try:
            await self.db.deleteOldTwitchMessages()
        except Exception as ex:
            await self.exception_reporter(ex, 'task_delete_old_messages')

    @log_exception_ignore(log=_get_logger)
    async def task_ping(self):
        await self.report_to_monitoring('/ping')

    @log_exception_ignore(log=_get_logger)
    async def task_test(self):
        self.logger.info('This is test task')

    @log_exception_ignore(log=_get_logger)
    async def task_task_error(self):
        self.logger.info('This is test task with an error')
        raise Exception("Exception from task_task_error")

    @log_exception_ignore(log=_get_logger)
    async def task_delete_old_auths(self):
        try:
            await self.db.deleteOldAuths()
        except Exception as ex:
            await self.exception_reporter(ex, 'task_delete_old_auths')

    async def migrate_chat_to_group(self, event):
        event_chat_id: int = int(get_peer_id(event.message.peer_id, add_mark=False))
        channel = await get_first(await event.client.db.get_auth_subchat(event_chat_id, skip_cache=True))

        if isinstance(event.message.to_id, PeerChat):
            # Is Chat type, need to migrate.
            try:
                self.logger.info("Migrating telegram Chat {} to telegram Channel".format(event_chat_id))
                migrated = self(functions.messages.MigrateChatRequest(chat_id=event_chat_id))
                self.logger.info(migrated)
                await event.reply('Done!')
            except Exception as ex:
                await self.report_exception(ex, "MigrateChatRequest for ID {} failed: \n".format(event_chat_id))
                await event.reply('Failed')

            if channel is not None:
                pass
                # TODO: migrate database id? need to check response fields
        else:
            self.logger.info("Checking database ID integrity...")
            # Already migrated to Channel type, but still need to verify if ID updated in database
            if channel is None:
                self.logger.info("Searching for for migrated chats due to request from {}".format(event_chat_id))

                channels = await event.client.db.get_auth_subchats()
                dialogs = await self.get_dialogs()
                migrated_chats = [dialog for dialog in dialogs if isinstance(dialog.entity, Chat) and dialog.entity.migrated_to is not None]

                for migrated_chat in migrated_chats:
                    if isinstance(migrated_chat.entity.migrated_to, InputChannel):
                        outdated_channel = next(filter(lambda row: row['tg_chat_id'] == migrated_chat.id, channels), None)
                        if not outdated_channel:
                            continue

                        updated_chat = next(filter(lambda row: isinstance(row.entity, Channel) and row.entity.id == migrated_chat.entity.migrated_to.channel_id, dialogs), None)
                        if not updated_chat:
                            continue

                        self.logger.info("Migrating channel_subchat_id {} telegram ID: from {} to {} ".format(outdated_channel['channel_subchat_id'], outdated_channel['tg_chat_id'], updated_chat.id))
                        await self.db.updateSubchatAfterJoin(outdated_channel['channel_subchat_id'], updated_chat.id, updated_chat.title, outdated_channel['join_link'])
            else:
                self.logger.info("Skipping migrate command because already migrated and linked")

    async def get_group_participant_full_data(self, channel, need_subs=True, need_follows=True, kick_not_verified=True, kick_deleted=True):
        self.logger.info('Collecting full data for channel {}'.format(channel['channel_id']))
        # Return value is data
        data = {'users': [], 'summary': {}}

        channel_entity = await self.get_entity(PeerChannel(channel['tg_chat_id']))
        participants = await self.get_participants(channel_entity)
        special_rights = await self.db.get_all_tg_chat_special_rights(channel_id=channel['channel_id'])

        group_admins = []
        bot_admin = False

        async for user in self.iter_participants(channel_entity, filter=ChannelParticipantsAdmins):
            group_admins.append(user)
            if user.id == self.me.id:
                bot_admin = True

        is_authorized = bool(channel['auth_status'])
        summary = {
                 'total': 0,
                 'bots': 0,
                 'deleted': 0,
                 'verified': 0,
                 'non_verified': 0,
                 'subs': 0,
                 'followers': 0,
                 'non_subs': 0,
                 'whitelists': 0,
                 'blacklists': 0,
                 'kicked': 0,
                 'sudos': 0,
                 'is_authorised': 1,
                 'next_mk': None,
                 'bot_admin': bot_admin}

        telegram_ids = [user.id for user in participants]
        kb_users = await self.db.getUsersByTgId(telegram_ids)
        twitch_ids = [user['tw_id'] for user in kb_users]
        twitch_ids_parts = split_array_into_parts(twitch_ids, 90)
        twitch_subs = []
        twitch_follows = []

        if need_subs:
            for twitch_ids_part in twitch_ids_parts:
                if not is_authorized:
                    continue

                try:
                    response = await self.api.twitch.get_channel_subs(broadcaster_id=channel['tw_id'], users=twitch_ids_part)
                    if response and 'data' in response and len(response['data']) > 0:
                        twitch_subs += response['data']
                except ExpiredAuthToken as err:
                    self.logger.exception(err)
                    is_authorized = False
                    continue
                except Exception as err:
                    self.logger.exception(err)
                    if 'unauthorized' in str(err).lower():
                        is_authorized = False
                        continue

                    # TODO: handle more stuff to increase stability
                    raise err

        # Clear if only part of information was received
        if not is_authorized:
            twitch_subs = []

        if need_follows and is_authorized:
            channel = await refresh_channel_token(channel)
            for twitch_id in twitch_ids:
                try:
                    response = await self.api.twitch.get_user_follows(channel_id=channel['tw_id'], users=[twitch_id], token=channel['token'])
                    if response and 'data' in response and len(response['data']) > 0:
                        twitch_follows += response['data']
                except ClientResponseError as err:
                    self.logger.exception(err)
                    raise err

        for user in participants:
            kb_user = next(filter(lambda kb: int(kb['tg_id']) == int(user.id), kb_users), None)
            tw_sub = next(filter(lambda tw: int(tw['user_id']) == int(kb_user['tw_id']), twitch_subs), None) if kb_user else None
            tw_follow = next(filter(lambda tw: int(tw['from_id']) == int(kb_user['tw_id']), twitch_follows), None) if kb_user else None
            is_whitelisted = next(filter(lambda right: right['user_id'] == kb_user['user_id'] and right['right_type'] == 'WHITELIST', special_rights), None) if kb_user else None
            is_blacklisted = next(filter(lambda right: right['user_id'] == kb_user['user_id'] and right['right_type'] == 'BLACKLIST', special_rights), None) if kb_user else None
            is_sudo = next(filter(lambda right: right['user_id'] == kb_user['user_id'] and right['right_type'] == 'SUDO', special_rights), None) if kb_user else None
            tg_admin = next(filter(lambda admin: admin.id == user.id, group_admins), None)

            if bot_admin and (kick_not_verified and kb_user is None and tg_admin is None and not user.bot or kick_deleted and user.deleted):
                await self.kick_user(channel_entity, user, channel['ban_time'])
                summary['kicked'] += 1
                continue

            user_summary = {
                'tg': user,
                'tg_admin': tg_admin,
                'kb': kb_user,
                'twitch': {
                    'sub': tw_sub,
                    'follow': tw_follow,
                },
                'is_deleted': user.deleted,
                'is_bot': user.bot,
                'is_whitelist': is_whitelisted,
                'is_blacklist': is_blacklisted,
                'is_sudo': is_sudo
            }

            summary['total'] += 1
            if user.bot:
                summary['bots'] += 1
            elif user.deleted:
                summary['deleted'] += 1
            else:
                # Not bot and not deleted
                if kb_user:
                    # Verified user
                    summary['verified'] += 1
                    if tw_sub:
                        summary['subs'] += 1
                    if tw_follow:
                        summary['followers'] += 1
                    if is_blacklisted:
                        summary['blacklists'] += 1
                    if is_whitelisted:
                        summary['whitelists'] += 1
                    if is_sudo:
                        summary['sudos'] += 1
                else:
                    summary['non_verified'] += 1

            data['users'].append(user_summary)

        summary['is_authorised'] = is_authorized
        summary['non_subs'] = summary['total'] - summary['subs'] - summary['bots'] - summary['deleted']
        if channel['kick_mode'] == 'PERIOD' and channel['auto_mass_kick'] and channel['auto_mass_kick'] > 0:
            summary['next_mk'] = channel['last_auto_kick'] + timedelta(days=channel['auto_mass_kick'])

        data['summary'] = summary
        return data

    @RedisHelper.listen_queue(queue_name=redis_key.get_tg_bot_requests())
    @log_exception(log=_get_logger, reporter=_get_reporter)
    async def on_remote_request(self, event):
        self.logger.info(event)
        if event['task'] == 'kick':
            tg_chat_id: int = int(event['tg_chat_id'])
            tg_user_id: int = int(event['tg_user_id'])

            try:
                await self(GetParticipantRequest(tg_chat_id, tg_user_id))
            except ValueError:
                self.logger.info("Skipping kick for user %s from %s due to missing participant", tg_chat_id, tg_user_id)
                # Could not find the input entity for PeerUser
                return

            self.logger.info("Kicking {} from {}, reason: {}".format(tg_user_id, tg_chat_id, event['reason']))
            kick_msg = await self.kick_participant(tg_chat_id, tg_user_id)
            if kick_msg:
                await kick_msg.delete()
        else:
            self.logger.info("Unhandled request type: %s", event)

    async def task_create_tasks_for_message_export(self):
        members = await self.db.getAllTgMembers()
        chats = await self.db.getTgChatAvailChannelsWithAuth()
        tasks = []
        ids = []
        for member in members:
            if member['tg_user_id'] not in ids:
                ids.append(member['tg_user_id'])

        users = await self.db.getUsersByTgId(ids)

        for member in members:
            user = next(filter(lambda row: row['tg_id'] == member['tg_user_id'], users), None)
            if not user:
                self.logger.info("Failed to find user data for member: {}".format(member))
                continue

            channel = next(filter(lambda row: row['tg_chat_id'] == member['tg_chat_id'] , chats), None)
            if not channel:
                self.logger.info("Failed to find channel data for member: {}".format(member))
                continue

            latest: TwitchMessage = await TwitchMessage.getLatestUserMessageInChannel(channel_id=channel['tw_id'], user_id=user['tw_id'])
            if latest and datetime.utcnow() - latest.sent_at > timedelta(days=7):
                self.logger.info("Skipping task creation for user {}".format(user))
                continue

            task = BotTask.createTask(TaskType.FETCH_TWITCH_MESSAGES, request={"channel_name": channel['name'], "user_id": user['tw_id']})
            tasks.append(task)

        if tasks:
            tasks[0].save(tasks)

    async def bot_task_processor(self):
        try:
            self.logger.info("Starting task scheduler")
            engine = Scheduler()
            await engine.run()
        except Exception as ex:
            await self.report_exception(ex, 'bot_task_processor')
