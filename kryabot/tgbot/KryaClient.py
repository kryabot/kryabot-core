from aiohttp import ClientResponseError
from telethon import TelegramClient
from telethon.errors import UserNotParticipantError, InviteHashInvalidError, InviteHashExpiredError
from telethon.extensions import html
from telethon.tl.functions.channels import LeaveChannelRequest, EditBannedRequest, GetParticipantRequest, \
    GetFullChannelRequest
from telethon.tl.types import PeerUser, PeerChannel, InputStickerSetID, \
    ChatInviteAlready, ChatInvite, ChatBannedRights, ChannelParticipantsAdmins, InputPeerChannel, ChatInvitePeek
from telethon.tl.functions.messages import ImportChatInviteRequest, GetAllStickersRequest, GetStickerSetRequest, \
    CheckChatInviteRequest, ExportChatInviteRequest
import os
import asyncio
import traceback
from datetime import datetime, date, timedelta
from object.Database import Database
from object.ApiHelper import ApiHelper
from object.Pinger import Pinger
from object.System import System
from object.Translator import Translator
from tgbot.Moderation import Moderation
import tgbot.events.handlers as krya_events
from tgbot.events.global_events.GlobalEventFactory import GlobalEventFactory

from utils.formatting import format_html_user_mention
from utils.decorators.exception import log_exception_ignore
from utils.value_check import avoid_none, is_empty_string, map_kick_setting
from utils.array import split_array_into_parts
from utils.twitch import refresh_channel_token, sub_check, get_active_oauth_data, sub_check_many, \
    refresh_channel_token_no_client
from tgbot.commands.commandbuilder import update_command_list
from tgbot.constants import TG_GROUP_MONITORING_ID, TG_SUPER_ADMINS
from utils.date_diff import get_datetime_diff_text
from utils import redis_key

global_logger = None
reporter = None
super_admins = TG_SUPER_ADMINS


class KryaClient(TelegramClient):
    def __init__(self, loop=None, logger=None, cfg=None):
        self.logger = logger
        self.cfg = cfg
        self.db = Database(loop=loop, size=self.cfg.getTelegramConfig()['MAX_SQL_POOL'])
        self.api = ApiHelper(reporter=self.exception_reporter, redis=self.db.redis)
        self.translator = None
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

        # For decorators
        global global_logger
        global reporter

        global_logger = logger
        reporter = self.exception_reporter

    async def start_bot(self):
        await self.update_data()
        self.logger.info('Creating db_activity task')
        self.loop.create_task(self.db.db_activity())
        self.logger.info('Creating task_oauth_refresher')
        self.loop.create_task(self.task_oauth_refresher())
        self.loop.create_task(Pinger(System.KRYABOT_TELEGRAM, self.logger, self.db.redis).run_task())
        self.loop.create_task(self.db.redis.start_listener(self.redis_subscribe))

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

    # List of subscribes executed during initialization
    async def redis_subscribe(self):
        await self.db.redis.subscribe_event(redis_key.get_streams_forward_data(), self.on_stream_update)

    async def init_moderation(self, channel_id=None):
        words = await self.db.getTgWords()
        if self.moderation is None:
            self.moderation = Moderation(self.logger, self.moderation_queue, self, cfg=self.cfg.getRedisConfig())

        await self.moderation.setWordList(words)

    async def init_translation(self):
        self.translator = Translator(await self.db.getTranslations(), self.logger)

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

    @log_exception_ignore(log=global_logger, reporter=reporter)
    async def restrict_user(self, channel_entity, user_entity, rights):
        await self(EditBannedRequest(channel_entity, user_entity, rights))

    @log_exception_ignore(log=global_logger, reporter=reporter)
    async def kick_user_from_channel(self, tg_chat_id, tg_user_id, ban_time):
        if not isinstance(tg_chat_id, PeerChannel):
            tg_chat_id = PeerChannel(int(tg_chat_id))

        if not isinstance(tg_user_id, PeerUser):
            tg_user_id = PeerUser(int(tg_user_id))

        await self.db.update_tg_stats_join(tg_chat_id)

        chat_entity = await self.get_entity(tg_chat_id)
        user_entity = await self.get_entity(tg_user_id)
        await self.kick_user(chat_entity, user_entity, ban_time)

    @log_exception_ignore(log=global_logger, reporter=reporter)
    async def kick_user(self, channel_entity, user_entity, ban_time):
        # print('kicking')
        # print(user_entity.stringify())
        rights = ChatBannedRights(
            until_date=timedelta(seconds=ban_time),
            view_messages=True)

        await self.restrict_user(channel_entity, user_entity, rights)

    @log_exception_ignore(log=global_logger, reporter=reporter)
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

        if channel is None:
            self.logger.error('Channel record not found for user ID {} and chat ID {}'.format(kb_user_id, chat_id[0]['tg_chat_id']))
            return

        if channel['refresh_status'] == 'WAIT':
            self.logger.info('Skipping channel {} refresh because current status is WAIT'.format(channel['tg_chat_id']))
            return

        await self.run_channel_refresh(channel, is_kick, params)

    @log_exception_ignore(log=global_logger, reporter=reporter)
    async def run_channel_refresh(self, channel, kick, params, silent=False):
        self.logger.info('Task: Refresh group members Channel: {}'.format(channel['channel_name']))
        self.logger.info('Kick: {} params: {}'.format(kick, params))
        report = '[Task]\nType: Refresh group members\nChannel: {}'.format(channel['channel_name'])
        report += '\nAuto-kick: {}'.format(kick)

        channel = await refresh_channel_token(client=self, channel=channel, force_refresh=True)
        channel_entity = await self.get_entity(PeerChannel(channel['tg_chat_id']))
        participants = await self.get_participants(channel_entity)

        if len(participants) == 0:
            await self.report_to_monitoring(report + '\nStatus: Failed\nReason: Empty telegram chat')
            return

        channel_admins = []
        async for user in self.iter_participants(channel_entity, filter=ChannelParticipantsAdmins):
            channel_admins.append(user)

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
        await self.db.startTgMemberRefresh(channel['tg_chat_id'])

        total = 0
        verified = 0
        subs = 0

        #self.logger.info('Refresh on channel: ' + str(channel))

        kick_array = []
        async with self.action(channel['tg_chat_id'], 'game'):
            for user in participants:
                sanity_check = 0

                while True:
                    if sanity_check > max_sanity_check:
                        break

                    error_message = ''
                    sanity_check += 1

                    self.logger.debug(str(user))
                    user_string = await avoid_none(user.first_name) + ' ' + await avoid_none(user.last_name) + ' ' + await avoid_none(user.username)
                    user_string.strip()

                    requestor = await self.db.getUserByTgChatId(user.id)
                    if len(requestor) == 0:
                        check_id = None
                    else:
                        check_id = requestor[0]['user_id']

                    user_whitelisted, user_blacklisted, blacklist_comment = await self.has_special_rights(check_id, user.id, channel)

                    if user.bot:
                        break

                    await asyncio.sleep(0.1)
                    total = total + 1

                    try:
                        sub_type = ''
                        if kickDeleted and user.deleted is True:
                            kicked_total += 1
                            kicked_deleted += 1
                            kick_array.append('{} (Deleted account)'.format(user.id))
                            self.logger.info(('[Deleted] Kicking: ' + user_string).encode())
                            await self.kick_user(channel_entity, user, channel['ban_time'])
                            break

                        if kick and user_blacklisted and not(user in channel_admins):
                            kicked_total += 1
                            kicked_blacklist += 1
                            kick_array.append('{} (Blacklisted account)'.format(user_string))
                            self.logger.info(('[Blacklisted] Kicking: ' + user_string).encode())
                            await self.kick_user(channel_entity, user, channel['ban_time'])
                            break

                        # Not verified
                        if len(requestor) == 0 and kickNonVerified and not user_whitelisted and not(user in channel_admins):
                            kicked_total += 1
                            kicked_not_verified += 1
                            kick_array.append('{} (Not verified)'.format(user_string))
                            self.logger.info(('[Not-verified] Kicking: ' + user_string).encode())
                            await self.kick_user(channel_entity, user, channel['ban_time'])
                            break

                        if len(requestor) > 0:
                            verified += 1

                            if channel['join_follower_only'] and kickNonFollower and not user_whitelisted and not(user in channel_admins):
                                try:
                                    follower_info = await self.api.twitch.check_channel_following(channel['tw_id'], requestor[0]['tw_id'])
                                    if follower_info and follower_info['total'] == 1:
                                        kicked_total += 1
                                        kicked_non_follow += 1
                                        kick_array.append('{} (Not follower: {})'.format(user_string, requestor[0]['name']))
                                        self.logger.info(('[Non-follower] Kicking: ' + user_string).encode())
                                        await self.kick_user(channel_entity, user, channel['ban_time'])
                                except Exception as e:
                                    await self.report_to_monitoring('Failed to check followage on user join for {uname}: {err}'.format(uname=requestor[0]['name'], err=str(e)))
                                    break

                            sub, sub_err = await sub_check(channel, requestor[0], self.db, self.api)

                            # Update token and repeat
                            if sub_err is not None and 'unauthorized' in sub_err.lower():
                                channel = await refresh_channel_token(self, channel, True)
                                verified -= 1
                                continue

                            if sub and len(sub['data']) > 0:
                                sub = sub['data'][0]
                            else:
                                sub = None

                            # Not a sub
                            if channel['join_sub_only'] and sub is None and kickNonSub and not user_whitelisted and not(user in channel_admins):
                                kicked_total += 1
                                kicked_non_sub += 1
                                kick_array.append('{} (Not subscriber: {})'.format(user_string, requestor[0]['name']))
                                self.logger.info(('[Non-sub] Kicking: ' + user_string).encode())
                                await self.kick_user(channel_entity, user, channel['ban_time'])
                                break

                            if sub is not None:
                                subs = subs + 1
                                sub_type = sub['tier']
                            else:
                                sub_type = 'No'

                        await self.db.saveTgMember(channel['tg_chat_id'],
                                                   user.id,
                                                   await avoid_none(user.first_name),
                                                   await avoid_none(user.last_name),
                                                   await avoid_none(user.username),
                                                   sub_type)
                    except Exception as e:
                        await self.report_exception(exception=e, info='User: {}'.format(user_string))

                        error_message = str(e)
                        self.logger.error(error_message)
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
                    break

                if sanity_check > max_sanity_check:
                    if not silent:
                        await self.send_message(channel['tg_chat_id'], self.translator.getLangTranslation(channel['bot_lang'], 'MASS_KICK_SANITY_STOP'))
                    break

        self.logger.debug('Mass kick loop finished')
        await self.db.finishTgMemberRefresh(channel['tg_chat_id'], error_message)
        if not silent:
            await self.report_to_monitoring(report + '\nStatus: Done\nTotal members: ' + str(total) + '\nVerified: ' + str(verified) + '\nSubscribers: ' + str(subs))

        if kick and not silent:
            await self.send_message(channel['tg_chat_id'], self.translator.getLangTranslation(channel['bot_lang'], 'MASS_KICK_FINISH'), parse_mode='html')
            await self.send_krya_love_sticker(channel['tg_chat_id'])

            if kicked_total > 0:
                kick_report = '<b>Total kicks: {}</b>\n'.format(kicked_total)
                if kicked_deleted > 0:
                    kick_report += '\nDeleted accounts: {}'.format(kicked_deleted)
                if kicked_blacklist > 0:
                    kick_report += '\nBanned users: {}'.format(kicked_blacklist)
                if kicked_not_verified > 0:
                    kick_report += '\nNot verified: {}'.format(kicked_not_verified)
                if kicked_non_follow > 0:
                    kick_report += '\nNot follower: {}'.format(kicked_non_follow)
                if kicked_non_sub > 0:
                    kick_report += '\nNot subscriber: {}'.format(kicked_non_sub)

                await self.send_message(channel['tg_chat_id'], kick_report)
            else:
                await self.send_message(channel['tg_chat_id'], '🙄 Nothing to kick :|')

            split_list = split_array_into_parts(kick_array, 50)
            is_first = True
            for kick_list in split_list:
                text = '\n'.join(kick_list)

                if is_first:
                    is_first = False
                    text = 'Kick list:\n\n{}'.format(text)
                await self.report_to_monitoring(text)

        await self.db.get_auth_subchat(channel['tg_chat_id'], skip_cache=True)
        await self.update_data()

    @log_exception_ignore(log=global_logger, reporter=reporter)
    async def is_whitelisted(self, kb_user_id, tg_user_id, channel)->bool:
        return bool(await self.has_special_right(kb_user_id, tg_user_id, channel, 'WHITELIST'))

    @log_exception_ignore(log=global_logger, reporter=reporter)
    async def is_blacklisted(self, kb_user_id, tg_user_id, channel)->bool:
        return bool(await self.has_special_right(kb_user_id, tg_user_id, channel, 'BLACKLIST'))

    @log_exception_ignore(log=global_logger, reporter=reporter)
    async def is_chatsudo(self, kb_user_id, tg_user_id, channel)->bool:
        return bool(await self.has_special_right(kb_user_id, tg_user_id, channel, 'SUDO'))

    @log_exception_ignore(log=global_logger, reporter=reporter)
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

    @log_exception_ignore(log=global_logger, reporter=reporter)
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

    #@log_exception_ignore(log=global_logger, reporter=reporter)
    async def run_user_report(self, channel, manual=False):
        channel = await refresh_channel_token(client=self, channel=channel, force_refresh=True)
        data = await self.get_group_participant_full_data(channel, need_follows=channel['join_follower_only'] == 1, kick_not_verified=not manual and channel['auto_kick'] == 1)
        lang = channel['bot_lang']
        summary = data['summary']
        self.logger.info("Summary for channel {}: {}".format(channel['channel_id'], summary))

        if manual is True or channel['show_report'] == 1:
            async with self.action(channel['tg_chat_id'], 'document'):
                report = self.translator.getLangTranslation(lang, 'UR_TITLE')
                report += '\n\n{label}: {val}'.format(val=summary['total'], label=self.translator.getLangTranslation(lang, 'UR_TOTAL'))
                report += '\n{label}: {val}'.format(val=summary['subs'], label=self.translator.getLangTranslation(lang, 'UR_SUBS'))
                report += '\n{label}: {val}'.format(val=(summary['non_subs']), label=self.translator.getLangTranslation(lang, 'UR_NON_SUBS'))
                if summary['follows'] > 0:
                    report += '\n{label}: {val}'.format(val=summary['follows'], label=self.translator.getLangTranslation(lang, 'UR_FOLLOWS'))
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
                    report += '\n{label}: {val}'.format(val=summary['blacklists'], label=self.translator.getLangTranslation(lang, 'UR_SUDO'))

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

    # @log_exception_ignore(log=global_logger, reporter=reporter)
    # async def get_user_report_data(self, channel):
    #     channel_entity = await self.get_entity(PeerChannel(channel['tg_chat_id']))
    #     participants = await self.get_participants(channel_entity)
    #
    #     channel_admins = []
    #     bot_admin = False
    #
    #     async for user in self.iter_participants(channel_entity, filter=ChannelParticipantsAdmins):
    #         channel_admins.append(user)
    #         if user.id == self.me.id:
    #             bot_admin = True
    #
    #     is_authotised = True
    #     channel_user_data = {'total': 0,
    #                          'bots': 0,
    #                          'deleted': 0,
    #                          'non_verified': 0,
    #                          'subs': 0,
    #                          'non_subs': 0,
    #                          'kicked': 0,
    #                          'whitelists': 0,
    #                          'blacklists': 0,
    #                          'is_authorised': 1,
    #                          'next_mk': None}
    #
    #     for user in participants:
    #         await asyncio.sleep(0.5)
    #         channel_user_data['total'] += 1
    #
    #         if user.bot:
    #             channel_user_data['bots'] += 1
    #         else:
    #             if await is_empty_string(user.first_name) and \
    #                     await is_empty_string(user.last_name) and \
    #                     await is_empty_string(user.username):
    #                 channel_user_data['deleted'] += 1
    #
    #             requestor = await self.db.getUserByTgChatId(user.id)
    #             if len(requestor) == 0:
    #                 channel_user_data['non_verified'] += 1
    #                 if bot_admin is True and channel['auto_kick'] == 1 and await self.is_whitelisted(None, user.id, channel) is False and not(user in channel_admins):
    #                     channel_user_data['kicked'] += 1
    #                     await self.kick_user(channel_entity, user, channel['ban_time'])
    #                 continue
    #
    #             if is_authotised:
    #                 is_sub = await self.api.is_sub_v2(channel, requestor[0], self.db)
    #                 if is_sub is None:
    #                     is_authotised = False
    #                     channel_user_data['is_authorised'] = 0
    #                 elif is_sub is True:
    #                     is_authotised = True
    #                     channel_user_data['is_authorised'] = 1
    #                     channel_user_data['subs'] += 1
    #
    #     special_rights = await self.db.get_tg_chat_special_rights(channel_id=channel['channel_id'])
    #     for right in special_rights:
    #         if right['channel_id'] == channel['channel_id']:
    #             channel_user_data['whitelists'] += 1 if right['right_type'] == 'WHITELIST' else 0
    #             channel_user_data['blacklists'] += 1 if right['right_type'] == 'BLACKLIST' else 0
    #
    #     channel_user_data['non_subs'] = channel_user_data['total'] - channel_user_data['bots'] - channel_user_data['subs']
    #
    #     if channel['auto_mass_kick'] and channel['auto_mass_kick'] > 0:
    #         channel_user_data['next_mk'] = channel['last_auto_kick'] + timedelta(days=channel['auto_mass_kick'])
    #
    #     return channel_user_data

    async def get_sticker_set(self, pack_name):
        for pack in (await self(GetAllStickersRequest(0))).sets:
            if pack.short_name == pack_name:
                pack_content = await self(GetStickerSetRequest(stickerset=InputStickerSetID(id=pack.id, access_hash=pack.access_hash)))
                return pack_content

        return None

    #@log_exception_ignore(log=global_logger, reporter=reporter)
    async def send_krya_sticker(self, chat_id, emo):
        kryabot_stickers = await self.get_sticker_set('KryaBot')
        for sticker in kryabot_stickers.packs:
            if sticker.emoticon == emo:
                for pack in kryabot_stickers.documents:
                    if sticker.documents[0] == pack.id:
                        await self.send_file(chat_id, pack)

    @log_exception_ignore(log=global_logger, reporter=reporter)
    async def join_channel(self, kb_user_id):
        report = '[Task]\nType: Channel join\nUser ID: ' + str(kb_user_id)
        chat_data = await self.db.getSubchatByUserId(kb_user_id)
        if chat_data is None or len(chat_data) == 0:
            await self.report_to_monitoring(report + " \n\nFailed, no chat found by user id!")
            return

        route = ''
        chat_data = chat_data[0]
        report += "\nChannel ID: " + str(chat_data['channel_id'])

        try:
            chat_check = await self(CheckChatInviteRequest(chat_data['join_link']))
            # Existing channel
            if type(chat_check) is ChatInviteAlready:
                if chat_check.chat.id == chat_data['tg_chat_id']:
                    await self.db.updateSubchatAfterJoin(chat_data['channel_subchat_id'], chat_check.chat.id, chat_check.chat.title.encode(), chat_data['join_link'])
                else:
                    # Tried to join other user channel, delete link and keep old ID
                    await self.db.updateSubchatAfterJoin(chat_data['channel_subchat_id'], chat_data['tg_chat_id'], chat_data['tg_chat_name'], '')
            # New channel provided
            elif type(chat_check) is ChatInvite:
                new_chat = await self(ImportChatInviteRequest(chat_data['join_link']))

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

    @log_exception_ignore(log=global_logger, reporter=reporter)
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
        refresh_period = 1800
        while True:
            try:
                auths = await self.db.getBotAuths()

                for auth in auths:
                    new_auth = await get_active_oauth_data(auth['user_id'], self.db, self.api, sec_diff=(refresh_period + 60))
            except Exception as e:
                self.logger.error(str(e))
                await self.exception_reporter(e, 'In task_oauth_refresher')
            await asyncio.sleep(refresh_period)

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
        self.logger.info('Searching for user {} in chat {}'.format(tg_user_id, tg_chat_id))
        try:

            channel_entity = await self.get_input_entity(int(tg_chat_id))
            user_entity = await self.get_input_entity(int(tg_user_id))
            return await self(GetParticipantRequest(channel=channel_entity, user_id=user_entity))
        except UserNotParticipantError:
            return None
        except ValueError:
            return None

    async def event_user_statistics(self):
        await self.update_data()
        for channel in (await self.db.get_auth_subchats()):
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
                await asyncio.sleep(1)

                try:
                    await self.kick_user_from_channel(ch['tg_chat_id'], unlink_tg_id, ch['ban_time'])
                    self.logger.info('Removed user {} from chat {}'.format(unlink_kb_id, ch['tg_chat_id']))
                    removed_from += ' ' + ch['tg_chat_id']
                except Exception as e:
                    continue

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

    @log_exception_ignore(log=global_logger)
    async def get_group_member_count(self, tg_group_id: int, skip_cache=False)->int:
        data = None
        if not skip_cache:
            data = await self.db.get_telegram_group_size_from_cache(tg_group_id)

        if data is None:
            data = (await self.get_participants(entity=int(tg_group_id), limit=0)).total
            await self.db.save_telegram_group_size_to_cache(tg_group_id, data)

        return int(data)

    @log_exception_ignore(log=global_logger)
    async def task_check_chat_publicity(self):
        chats = await self.get_all_auth_channels()

        for chat in chats:
            if chat['tg_chat_id'] == 0:
                continue

            # Already paused
            if chat['force_pause'] == 1:
                continue

            await asyncio.sleep(60)
            try:
                full_info = await self(GetFullChannelRequest(channel=chat['tg_chat_id']))
                channel = full_info.chats[0]
                if full_info.full_chat.linked_chat_id is not None and full_info.full_chat.linked_chat_id > 0:
                    self.logger.info("Group {} linked to {}".format(chat['tg_chat_id'], full_info.full_chat.linked_chat_id))
                    await self.report_to_monitoring("Force pausing channel {} ({}) because linked to channel {}".format(channel.title, channel.id,full_info.full_chat.linked_chat_id))
                    await self.db.updateChatForcePause(chat['tg_chat_id'], True)
                elif channel.username is not None and len(channel.username) > 0:
                    self.logger.info("Group {} has username {}".format(chat['tg_chat_id'], channel.username))
                    await self.report_to_monitoring("Force pausing channel {} ({}) because it has username {}".format(channel.title, channel.id, channel.username))
                    await self.db.updateChatForcePause(chat['tg_chat_id'], True)
            except Exception as ex:
                await self.report_exception(ex, info=chat)

    @log_exception_ignore(log=global_logger)
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

    @log_exception_ignore(log=global_logger)
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

    @log_exception_ignore(log=global_logger)
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

    @log_exception_ignore(log=global_logger)
    async def task_delete_old_messages(self):
        try:
            await self.db.deleteOldTwitchMessages()
        except Exception as ex:
            await self.exception_reporter(ex, 'task_delete_old_messages')

    @log_exception_ignore(log=global_logger)
    async def task_ping(self):
        await self.report_to_monitoring('/ping')

    @log_exception_ignore(log=global_logger)
    async def task_test(self):
        self.logger.info('This is test task')

    @log_exception_ignore(log=global_logger)
    async def task_task_error(self):
        self.logger.info('This is test task with an error')
        raise Exception("Exception from task_task_error")

    async def get_group_participant_full_data(self, channel, need_subs=True, need_follows=True, kick_not_verified=True):
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

        is_authorized = True
        summary = {
                 'total': 0,
                 'bots': 0,
                 'deleted': 0,
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
                    response, errors = await sub_check_many(channel, twitch_ids_part, self.db, self.api)
                    if errors:
                        raise Exception(errors)
                    if response and 'data' in response and len(response['data']) > 0:
                        twitch_subs += response['data']
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
            channel = await refresh_channel_token_no_client(channel, self.db, self.api)
            for twitch_id in twitch_ids:
                try:
                    response = await self.api.twitch.get_channel_follows(channel_id=channel['tw_id'], users=[twitch_id], token=channel['token'])
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

            if bot_admin and (kick_not_verified and kb_user is None and tg_admin is None and not user.bot or user.deleted):
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
        if channel['auto_mass_kick'] and channel['auto_mass_kick'] > 0:
            summary['next_mk'] = channel['last_auto_kick'] + timedelta(days=channel['auto_mass_kick'])

        data['summary'] = summary
        return data
