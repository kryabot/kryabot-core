import asyncio
from typing import List

import aiomysql
from object.BotConfig import BotConfig
from object.SqlSwitch import getSql
from aiomysql import pool
import time
import logging
from object.RedisHelper import RedisHelper
import utils.redis_key as redis_key


class Database:
    def __init__(self, loop, size=-1, cfg=None):
        if loop is None:
            loop = asyncio.get_event_loop()

        self.logger = logging.getLogger('krya.db')
        self.logger.info('Database init')
        self.loop = loop
        self.active = False
        self.last_activity = time.time()
        self.max_error_count = 5
        self.max_size = size
        if cfg is None:
            cfg = BotConfig()

        self.cfg = cfg

        self.redis = RedisHelper(self.cfg.getRedisConfig()['HOST'],
                                 self.cfg.getRedisConfig()['PORT'],
                                 self.cfg.getRedisConfig()['PASSWORD'],
                                 minsize=1,
                                 maxsize=5,
                                 loop=self.loop)

    async def connection_init(self):
        self.logger.debug('Opening SQL connections')
        cfg = self.cfg
        if self.max_size == -1:
            self.max_size = cfg.getSQLConfig()['MAX_POOL']

        self.connection_pool = await pool._create_pool(maxsize=self.max_size,
                                                       host=cfg.getSQLConfig()['HOST'],
                                                       port=cfg.getSQLConfig()['PORT'],
                                                       user=cfg.getSQLConfig()['USER'],
                                                       password=cfg.getSQLConfig()['PASSWORD'],
                                                       db=cfg.getSQLConfig()['DB'],
                                                       loop=self.loop,
                                                       use_unicode=True,
                                                       charset=cfg.getSQLConfig()['CHARSET'])
        await self.update_activity()

    async def db_activity(self):
        while True:
            await asyncio.sleep(30)
            await self.activity_check()

    async def connection_close(self):
        self.logger.info('Closing SQL connections')
        self.connection_pool.terminate()
        self.active = False

    async def activity_check(self):
        if self.active and time.time() - self.last_activity > 300:
            await self.connection_close()

    async def update_activity(self):
        self.active = True
        self.last_activity = time.time()

    async def query(self, query_key, params):
        sql_query = await getSql(query_key)
        return await self.do_query(sql_query, params)

    async def do_query(self, query, params):
        current_error_count = 0

        if not self.active:
            await self.connection_init()

        while True:
            async with self.connection_pool.acquire() as conn:
            #print('Free connections: ' + str(self.connection_pool.freesize))
                try:
                    if current_error_count >= self.max_error_count:
                        return

                    cursor = await conn.cursor(aiomysql.DictCursor)
                    await cursor.execute(query, params)
                    await conn.commit()
                    await self.update_activity()
                    result = await cursor.fetchall()
                    return result
                except Exception as e:
                    if 'Unhandled user-defined exception condition' in str(e):
                        break
                    current_error_count = current_error_count + 1
                    self.logger.error('{name}: {error}'.format(name=e.__class__.__name__, error=str(e)))
                    self.logger.info(query)
                    self.logger.info(str(params))
                    await asyncio.sleep(0.1)
                    continue
                #break

    async def queryProc(self, procName, params):
        current_error_count = 0

        if not self.active:
            await self.connection_init()

        while True:
            async with self.connection_pool.acquire() as conn:
                try:
                    if current_error_count >= self.max_error_count:
                        return
                    self.logger.info(procName)
                    self.logger.info(params)
                    async with conn.cursor() as cur:
                        await cur.callproc(procName, params)
                        await self.update_activity()
                        return await cur.fetchall()
                except Exception as e:
                    current_error_count = current_error_count + 1
                    self.logger.error('{name}: {error}'.format(name=e.__class__.__name__, error=str(e)))
                    self.logger.info(procName)
                    self.logger.info(str(params))
                    await asyncio.sleep(0.1)
                    continue

    async def getAutojoinChannels(self):
        return await self.query('find_auto_join', [])

    async def createChannelRecord(self, channel_name):
        return await self.query('create_channel', [channel_name])

    async def getChannel(self, channel_name):
        return await self.query('find_channel', [channel_name])

    async def get_channel_by_twitch_id(self, tw_user_id):
        return await self.query('find_channel_by_tw_id', [tw_user_id])

    async def createUserRecord(self, twitch_id, username, display_name):
        return await self.query('create_user', [twitch_id, username, display_name])

    async def getUserRecordByTwitchId(self, twitch_id, skip_cache=False):
        cache_key = redis_key.get_kb_user(twitch_id=twitch_id)

        data = None
        if not skip_cache:
            data = await self.redis.get_parsed_value_by_key(cache_key)

        if data is None:
            data = await self.query('find_user_by_tw_id', [twitch_id])
            if data is not None:
                await self.redis.set_parsed_value_by_key(cache_key, data, expire=redis_key.ttl_day)
        return data

    async def get_admins(self):
        return await self.query('find_admins', [])

    async def getChannelNotices(self):
        return await self.query('find_channel_notices', [])

    async def getNoticeTypes(self):
        return await self.query('find_notice_types', [])

    async def createResponseRecord(self, request_id, tg_id, tg_name, tg_second_name, tg_tag):
        return await self.query('add_response', [request_id, tg_id, tg_name, tg_second_name, tg_tag])

    async def getResponseByRequest(self, request_id):
        return await self.query('find_response_by_request', [request_id])

    async def getResponseByChatId(self, tg_id):
        return await self.query('find_response_by_chat_id', [tg_id])

    async def getUserById(self, user_id):
        return await self.query('find_user_by_id', [user_id])

    async def updateUserTwitchId(self, user_id, twitch_id):
        return await self.query('update_user_twitch_id', [twitch_id, user_id])

    async def update_telegram_group_name(self, tg_group_id: int, new_title: str):
        return await self.query('update_tg_chat_name', [new_title, tg_group_id])

    async def getTgChatAvailChannelsWithAuth(self):
        return await self.query('find_all_tg_channels_with_auth', [])

    async def get_settings(self):
        return await self.query('get_settings', [])

    async def get_setting(self, setting_key: str, skip_cache=False):
        cache_key = redis_key.get_setting(setting_key)

        data = None
        if not skip_cache:
            data = await self.redis.get_parsed_value_by_key(cache_key)

        if data is None:
            data = await self.query('get_setting', [setting_key])
            await self.redis.set_parsed_value_by_key(cache_key, data, expire=redis_key.ttl_minute * 10)
        return data


    async def saveBotAuth(self, kb_user_id, token, refresh_token, expires_in):
        return await self.query('save_bot_refresh_token', [kb_user_id, token, refresh_token, expires_in])

    async def getUserByTgChatId(self, tg_user_id, skip_cache=False):
        cache_key = redis_key.get_kb_user_by_tg_id(tg_id=tg_user_id)

        data = None
        if not skip_cache:
            data = await self.redis.get_parsed_value_by_key(cache_key)

        if data is None:
            data = await self.query('get_user_by_tg_id', [tg_user_id])
            await self.redis.set_parsed_value_by_key(cache_key, data, expire=redis_key.ttl_hour)
        return data

    async def getUsersByTgId(self, tg_users: [int]):
        if tg_users is None or len(tg_users) == 0:
            raise ValueError('tg_users must have atleast one entry!')

        param_placeholders = ','.join(['%s'] * len(tg_users))
        sql = await getSql('get_users_by_tg_id')
        sql = sql % param_placeholders
        response = await self.do_query(sql, tg_users)
        if response:
            for item in response:
                await self.redis.set_parsed_value_by_key(redis_key.get_kb_user_by_tg_id(tg_id=item['tg_id']), [item], expire=redis_key.ttl_hour)
        return response

    async def updateSubchatAfterJoin(self, channel_subchat_id,  chat_id, chat_name, link):
        return await self.query('save_chat_info_after_join', [chat_id, chat_name, link, channel_subchat_id])

    async def deleteTgMembers(self, chat_id):
        return await self.query('delete_tg_members', [chat_id])

    async def saveTgMember(self, chat_id, user_id, first_name, second_name, username, sub_type):
        return await self.query('add_tg_member', [chat_id, user_id, first_name, second_name, username, sub_type])

    async def startTgMemberRefresh(self, chat_id):
        await self.deleteTgMembers(chat_id)
        return await self.query('update_member_refresh_sta', ['WAIT', chat_id])

    async def finishTgMemberRefresh(self, chat_id, err):
        if err is None or err == '':
            return await self.query('update_member_refresh_sta', ['DONE', chat_id])
        else:
            return await self.query('update_member_refresh_sta', ['ERR', chat_id])

    async def selectExisingActiveRequestsByCode(self, code):
        return await self.query('check_generated_id', [code])

    async def verifyToken(self, token):
        params = (token, None, None, None)
        return await self.queryProc('validateWebToken', params)

    async def banTgMedia(self, channelId, mediaType, mediaId, userId, desc):
        return await self.query('add_tg_ban_media', [channelId, mediaType, mediaId, userId, desc])

    async def getBannedMedia(self):
        return await self.query('get_banned_media', [])

    async def createMessage(self, channel_id, user_id, message):
        return await self.query('create_message', [channel_id, user_id, message])

    async def searchTwitchMessages(self, channel_id, text):
        return await self.query('search_twitch_messages', [channel_id, text])

    async def getChatMostActiveUser(self, channel_id, within_last_seconds):
        return await self.query('get_twitch_message_most_active_user', [channel_id, within_last_seconds])

    async def getChatMessageCount(self, channel_id, within_last_seconds):
        return await self.query('get_twitch_message_message_count', [channel_id, within_last_seconds])

    async def deleteOldTwitchMessages(self):
        return await self.query('wipe_twitch_messages', [])

    async def deleteOldAuths(self):
        return await self.query('delete_old_auths', [])

    async def saveTwitchMassBan(self, channel_id, user_id, ban_text, ban_time, ban_count):
        return await self.query('save_mass_ban', [channel_id, user_id, ban_text, ban_time, ban_count])

    async def createNotice(self, channel_id, user_id, notice_type, tier, count1, count2, target_id):
        return await self.query('create_notice', [channel_id, user_id, notice_type, tier, count1, count2, target_id])

    async def getLastSubHistoricalInfo(self, channel_id, user_id):
        return await self.query('get_last_sub_info', [channel_id, user_id])

    async def addUserToWhitelist(self, channel_id, user_id, tg_user_id, first_name, last_name, user_name, by_user_id, comment):
        return await self.query('sp_saveTgSpecialRight', ['WHITELIST', channel_id, user_id, tg_user_id, first_name, last_name, user_name, by_user_id, comment])

    async def addUserToBlacklist(self, channel_id, user_id, tg_user_id, first_name, last_name, user_name, by_user_id, comment):
        return await self.query('sp_saveTgSpecialRight', ['BLACKLIST', channel_id, user_id, tg_user_id, first_name, last_name, user_name, by_user_id, comment])

    async def addUserToSudo(self, channel_id, user_id, tg_user_id, first_name, last_name, user_name, by_user_id, comment):
        return await self.query('sp_saveTgSpecialRight', ['SUDO', channel_id, user_id, tg_user_id, first_name, last_name, user_name, by_user_id, comment])

    async def removeTgSudoRight(self, channel_id, tg_user_id):
        return await self.query('remove_sudo_right', [channel_id, tg_user_id])

    async def removeTgSpecialRight(self, kb_user_id, tg_user_id):
        return await self.query('sp_deleteTgSpecialRight', [kb_user_id, tg_user_id])

    async def updateAutoMassKickTs(self, subchat_id, next_date):
        return await self.query('update_auto_mass_kick_ts', [next_date, subchat_id])

    async def getResubHistory(self, channel_id, user_id):
        return await self.query('get_resub_info', [channel_id, user_id])

    async def getSubgiftHistory(self, channel_id, user_id):
        return await self.query('get_subgift_info', [channel_id, user_id, user_id])

    async def updateAward(self, channel_user_id, award_id, award_key, award_template, creator_id):
        return await self.query('update_tg_award', [channel_user_id, award_id, award_key, award_template, creator_id])

    async def setTgAwardForUser(self, award_id, tg_user_id, cnt):
        return await self.query('sp_updateUserTgAward', [award_id, tg_user_id, cnt])

    async def getUserTgAwards(self, channel_name, tg_user_id):
        return await self.query('sp_getTgUserAwards', [channel_name, tg_user_id])

    async def getChannelTgAwards(self, channel_id, user_id, skip_cache=False):
        cache_key = redis_key.get_tg_channel_awards(channel_id)
        data = None

        if not skip_cache:
            data = await self.redis.get_parsed_value_by_key(cache_key)

        if data is None:
            data = await self.query('get_tg_awards', [user_id])
            await self.redis.set_parsed_value_by_key(cache_key, data, redis_key.ttl_week)

        return data

    async def deleteTgAward(self, channel_user_id, award_id, user_id):
        return await self.query('sp_deleteTgAward', [channel_user_id, award_id, user_id])

    async def setTgGetter(self, channel_id, keyword, text, cache_message_id, user_id, access):
        return await self.query('set_getter', [channel_id, keyword, text, str(cache_message_id), user_id, access])

    async def getTgGetter(self, channel_id, keyword):
        return await self.query('get_getter', [channel_id, keyword])

    async def deleteTgGetter(self, channel_user_id, getter_id, deleted_by):
        return await self.query('delete_getter', [channel_user_id, getter_id, deleted_by])

    async def getAllTgGetters(self, channel_id):
        return await self.query('get_all_getters', [channel_id])

    async def getRemindersByUserId(self, user_id):
        return await self.query('sp_getRemindersByUserId', [user_id])

    async def saveReminderByUserId(self, user_id, reminder_id, reminder_key, reminder_text, is_completed):
        return await self.query('sp_saveReminderByUserId', [user_id, reminder_id, reminder_key, reminder_text, is_completed])

    async def deleteReminderById(self, user_id, reminder_id):
        return await self.query('sp_deleteReminderById', [user_id, reminder_id])

    async def updateLastReminder(self, subchat_id):
        return await self.query('sp_updateLastTgReminder', [subchat_id])

    async def saveReminderCooldown(self, subchat_id, cooldown):
        return await self.query('save_reminder_cooldown', [cooldown, subchat_id])

    async def getSubchatByUserId(self, user_id):
        return await self.query('get_subchat_by_user', [user_id])

    async def getTranslations(self):
        return await self.query('get_translations', [])

    async def sebBotLang(self, subchat_id, lang):
        return await self.query('set_bot_lang', [lang, subchat_id])

    async def getTgWords(self):
        return await self.query('get_tg_words', [])

    async def addTgWord(self, subchat_id, type_id, word, user_id):
        return await self.query('add_tg_word', [subchat_id, type_id, word, user_id])

    async def deleteTgWord(self, subchat_id, word):
        return await self.query('delete_tg_word', [subchat_id, word])

    async def getLinkageDataByTwitchId(self, twitch_id):
        return await self.query('get_linkage_date', [twitch_id])

    async def deleteTelegramLink(self, user_id):
        return await self.query('sp_deleteTgLink', [user_id])

    async def getSubchatWithAuth(self, tg_chat_id):
        return await self.query('get_tg_chat_with_auth', [tg_chat_id])

    async def updateUserTwitchName(self, kb_user_id, new_name, new_display_name, tg_user_id=None, tw_user_id=None):
        await self.query('update_user_name', [new_name, new_display_name, kb_user_id])

        # Update data in cache
        if tw_user_id is not None:
            await self.getUserRecordByTwitchId(tw_user_id, skip_cache=True)

        if tg_user_id is not None:
            await self.getUserByTgChatId(tg_user_id, skip_cache=True)

    async def updateSubchatMode(self, tg_chat_id, follow_only, sub_only):
        await self.query('set_subchat_mode', [follow_only, sub_only, tg_chat_id])
        await self.get_auth_subchat(tg_chat_id, skip_cache=True)

    async def updateSubchatEntrance(self, tg_chat_id, enabled):
        await self.query('set_subchat_entrance', [enabled, tg_chat_id])
        await self.get_auth_subchat(tg_chat_id, skip_cache=True)

    async def updateSubchatMaxWarns(self, tg_chat_id, max_warns):
        await self.query('set_subchat_max_warns', [max_warns, tg_chat_id])
        await self.get_auth_subchat(tg_chat_id, skip_cache=True)

    async def updateSubchatWarnExpireHours(self, tg_chat_id, expire_in):
        await self.query('set_subchat_warn_expire', [expire_in, tg_chat_id])
        await self.get_auth_subchat(tg_chat_id, skip_cache=True)

    async def updateSubchatWarnMuteHours(self, tg_chat_id, mute_time):
        await self.query('set_subchat_warn_mute_hours', [mute_time, tg_chat_id])
        await self.get_auth_subchat(tg_chat_id, skip_cache=True)

    async def getTgChatIdByUserId(self, kb_user_id):
        return await self.query('get_tg_chat_id_by_kb_user_id', [kb_user_id])

    async def getTgChatIdByChannelId(self, channel_id):
        return await self.query('get_tg_chat_id_by_channel_id', [channel_id])

    async def saveTwitchSubEvent(self, channel_id, kb_user_id, event_id, event_type, event_ts, is_gift, tier, message):
        return await self.query('save_sub_event', [channel_id, kb_user_id, event_id, event_type, event_ts, is_gift, tier, message])

    async def getBotAuthByUserId(self, kb_user_id):
        return await self.query('get_bot_auth_by_user_id', [kb_user_id])

    async def getBotAuths(self):
        return await self.query('get_all_bot_auths', [])

    async def getTwitchEventByEventId(self, event_id):
        return await self.query('get_twitch_subdata', [event_id])

    async def getResponseByUserId(self, user_id):
        return await self.query('find_response_by_user_id', [user_id])

    async def setSubchatActionOnRefund(self, tg_chat_id, action):
        await self.query('set_subchat_action_on_refund', [action, tg_chat_id])
        await self.get_auth_subchat(tg_chat_id, skip_cache=True)

    async def setSubchatActionOnStream(self, tg_chat_id, action):
        await self.query('set_subchat_action_on_stream', [action, tg_chat_id])
        await self.get_auth_subchat(tg_chat_id, skip_cache=True)

    async def setSubchatKickPeriod(self, tg_chat_id, new_period):
        await self.query('set_subchat_mass_kick_period', [new_period, tg_chat_id])
        await self.get_auth_subchat(tg_chat_id, skip_cache=True)

    async def setSubchatMinSubMonths(self, tg_chat_id, min_months):
        await self.query('set_subchat_min_sub_months', [min_months, tg_chat_id])
        await self.get_auth_subchat(tg_chat_id, skip_cache=True)

    async def setUserSocVk(self, kb_user_id, link):
        await self.query('set_user_soc_vk', [link, kb_user_id])

    async def setUserSocInst(self, kb_user_id, link):
        await self.query('set_user_soc_inst', [link, kb_user_id])

    async def setUserSocUt(self, kb_user_id, link):
        await self.query('set_user_soc_ut', [link, kb_user_id])

    async def setWelcomeMessageId(self, tg_chat_id, message_id):
        await self.query('set_welcome_message_id', [message_id, tg_chat_id])
        await self.get_auth_subchat(tg_chat_id, skip_cache=True)

    async def getTwitchSubHistoryRecords(self, channel_id, user_id):
        return await self.query('get_sub_history', [channel_id, user_id])

    async def getTwitchSubNotificationHistory(self, channel_id, user_id):
        return await self.query('get_sub_notice_history', [channel_id, user_id])

    async def getTgVoteActive(self, channel_id):
        return await self.query('get_tg_vote_active', [channel_id])

    async def createTgVote(self, channel_id, description, created_by):
        await self.query('create_tg_vote', [channel_id, description, created_by])

    async def finishTgVote(self, vote_id):
        await self.query('finish_tg_vote', [vote_id])

    async def addTgVoteNominee(self, vote_id, nominee_user_id, adder_user_id):
        await self.query('add_tg_vote_nominate', [vote_id, nominee_user_id, adder_user_id])

    async def addTgVoteIgnore(self, vote_id, nominee_user_id, adder_user_id):
        await self.query('add_tg_vote_ignore', [vote_id, nominee_user_id, adder_user_id])

    async def deleteTgVoteMember(self, vote_id, nominee_user_id):
        await self.query('delete_tg_vote_nominee', [vote_id, nominee_user_id])

    async def addTgVotePoint(self, vote_id, nominee_user_id, voter_user_id):
        await self.query('add_tg_vote_point', [vote_id, nominee_user_id, voter_user_id])

    async def tgVoteOpenNominations(self, vote_id):
        await self.query('tg_vote_nomination_access', [1, vote_id])

    async def tgVoteCloseNominations(self, vote_id):
        await self.query('tg_vote_nomination_access', [0, vote_id])

    async def getTgVoteNominee(self, vote_id, nominee_user_id):
        return await self.query('get_tg_vote_nominee_by_user', [vote_id, nominee_user_id])

    async def getTgVoteNominees(self, vote_id):
        return await self.query('get_tg_vote_nominees', [vote_id])

    async def hideSubchatReport(self, tg_chat_id):
        await self.query('update_subchat_report_visibility', [0, tg_chat_id])
        await self.get_auth_subchat(tg_chat_id, skip_cache=True)

    async def showSubchatReport(self, tg_chat_id):
        await self.query('update_subchat_report_visibility', [1, tg_chat_id])
        await self.get_auth_subchat(tg_chat_id, skip_cache=True)

    async def enableGlobalEvents(self, tg_chat_id):
        await self.query('update_channel_global_events', [1, tg_chat_id])
        await self.get_auth_subchat(tg_chat_id, skip_cache=True)

    async def disableGlobalEvents(self, tg_chat_id):
        await self.query('update_channel_global_events', [0, tg_chat_id])
        await self.get_auth_subchat(tg_chat_id, skip_cache=True)

    async def getAllTgMembers(self):
        return await self.query('get_all_tg_members', [])

    async def getChannelPointActions(self, channel_id=None):
        if channel_id is not None:
            return await self.query('get_point_actions_by_channel', [channel_id])
        else:
            return await self.query('get_point_actions', [])

    async def getChannelCommands(self, channel_id=None):
        def merge(cmds, options):
            for cmd in cmds:
                if 'options' not in cmd:
                    cmd['options'] = []
                for option in options:
                    if option['channel_command_id'] == cmd['channel_command_id']:
                        cmd['options'].append(option)

            return cmds

        if channel_id is None:
            cmds, options = await asyncio.gather(*[self.query('find_channel_commands', []), self.query('find_channel_command_options', [])], return_exceptions=True)
        else:
            cmds, options = await asyncio.gather(*[self.query('find_channel_commands_by_id', [channel_id]), self.query('find_channel_command_options_by_id', [channel_id])], return_exceptions=True)

        if isinstance(cmds, Exception):
            raise cmds
        if isinstance(options, Exception):
            raise options

        return merge(cmds, options)

    async def getChannelSongs(self, channel_id=None):
        if channel_id is None:
            return await self.query('get_songs_all', [])
        else:
            return await self.query('get_songs_by_channel', [channel_id])

    async def getTgHistoricalStats(self, channel_id: int, stat_type: str, days_old: int):
        return await self.query('get_tg_historical_stats', [channel_id, stat_type, days_old])

    async def getChannelByUserId(self, kb_user_id):
        return await self.query('get_channel_by_user_id', [kb_user_id])

    async def getGlobalEventUserDataByEvent(self, global_event_id, user_id):
        return await self.query('get_global_event_user_data_by_event', [global_event_id, user_id])

    async def setGlobalEventDataForUser(self, event_id, user_id, new_amount, new_val):
        await self.query('set_global_event_user_reward', [event_id, user_id, new_amount, new_val])

    async def getGlobalUserAwards(self, user_id):
        return await self.query('get_global_user_awards', [user_id])

    async def updateCommandUsage(self, command_id):
        await self.query('update_command_usage', [command_id])

    async def getInstagramProfiles(self):
        return await self.query('get_instagram_profiles', [])

    async def getInstagramHistory(self):
        return await self.query('get_instagram_history', [])

    async def getAllActiveInfoBots(self):
        return await self.query('get_all_active_info_bots', [])

    async def getAllNewInfoBots(self):
        return await self.query('get_all_new_info_bots', [])

    async def getAllInfoBotLinks(self):
        return await self.query('get_all_info_bots_links', [])

    async def getUserRightsInChannel(self, channel_id, user_id):
        return await self.query('get_user_rights_in_channel', [channel_id, user_id])

    async def createInfoBot(self, tg_chat_id: int, name: str, lang: str = 'ru'):
        return await self.query('create_infobot', [tg_chat_id, name, lang])

    async def getInfobotLinks(self, infobot_id: int):
        return await self.query('get_infobot_links', [infobot_id])

    async def getInfobotLinksByType(self, infobot_id: int, link_table: str):
        return await self.query('get_infobot_links_by_type', [infobot_id, link_table])

    async def getInfobotTwitchLinks(self, infobot_id: int):
        return await self.query('get_infobot_twich_links', [infobot_id])

    async def saveInfoBotLinkConfig(self, infobot_id: int, link_type: str, link_id: int, new_config):
        return await self.query('save_infobot_config', [new_config, infobot_id, link_type, link_id])

    async def deleteInfoBotLink(self, infobot_id: int, link_type: str, link_id: int):
        return await self.query('delete_infobot_link', [infobot_id, link_type, link_id])

    async def updateInfoTargetData(self, infobot_id, target_id, target_name, join_data):
        await self.query('update_info_target_data', [target_name, target_id, join_data, infobot_id])

    async def getInfoBotByUser(self, user_id):
        return await self.query('get_infobot_by_user', [user_id])

    async def getInfoBotByChat(self, tg_chat_id, skip_cache=False):
        cache_key = redis_key.get_infobot_target(tg_chat_id)
        data = None

        if not skip_cache:
            data = await self.redis.get_parsed_value_by_key(cache_key)

        if data is None:
            data = await self.query('get_infobot_by_chat', [tg_chat_id])
            if data:
                await self.redis.set_parsed_value_by_key(cache_key, data[0], redis_key.ttl_day)

        return data

    async def saveInstagramPostEvent(self, profile_id, media_id, date):
        await self.query('save_instagram_event', ['POST', profile_id, media_id, date])

    async def saveInstagramStoryEvent(self, profile_id, media_id, date):
        await self.query('save_instagram_event', ['STORY', profile_id, media_id, date])

    async def getTwitchProfiles(self):
        return await self.query('get_all_twitch_profiles', [])

    async def getTwitchHistory(self):
        return await self.query('get_all_twitch_history', [])

    async def getBoostyProfiles(self):
        return await self.query('get_boosty_profiles', [])

    async def getBoostyHistory(self):
        return await self.query('get_boosty_history', [])

    async def saveBoostEvent(self, event):
        await self.query('save_boosty_event', [event.profile.profile_id, event.publish_time, event.id])

    async def getTgInvite(self, channel_id, user_id):
        return await self.query('get_tg_active_invite', [channel_id, user_id])

    async def saveTgInvite(self, channel_id, user_id, by_user_id):
        await self.query('save_tg_active_invite', [channel_id, user_id, by_user_id])

    async def markInvitationUsed(self, channel_id, user_id):
        await self.query('mark_invitation_used', [channel_id, user_id])

    async def saveSpamLog(self, channel_name, sender, message, ts):
        await self.query('save_spam_log', [channel_name, sender, message, ts])

    async def getUserAllCurrency(self, user_id):
        return await self.query('get_user_all_currencies', [user_id])

    async def getTgChatCurrency(self, channel_id):
        return await self.query('get_channel_currency', [channel_id])

    async def updateChatForcePause(self, tg_chat_id, force_pause):
        await self.query('update_subchat_forced_pause', [force_pause, tg_chat_id])
        await self.get_auth_subchat(tg_chat_id, skip_cache=True)

    async def updateInviteLink(self, tg_chat_id, new_link):
        await self.query('update_invite_link', [new_link, tg_chat_id])

    async def registerTwitchProfile(self, user_id):
        await self.query('register_profile_twitch', [user_id])

    async def getTwitchProfileByUserId(self, user_id):
        return await self.query('get_infobot_twitch_profile', [user_id])

    async def createInfobotProfileLink(self, infobot_id: int, profile_type: str, profile_id: int):
        return await self.query('create_infobot_link', [infobot_id, profile_type, profile_id])

    async def updateSubchatAuthStatus(self, subchat_id, status):
        await self.query('set_subchat_auth_status', [status, subchat_id])

    async def get_list_values_full(self, list_name):
        return await self.query('get_active_list_values', [list_name])

    async def add_currency_to_user(self, currency_key: str, user_id: int, amount: int):
        return await self.query('add_currency_to_user', [currency_key, user_id, amount])

    async def add_currency_to_all_chat_users(self, currency_key: str, tg_chat_id: int, amount: int):
        return await self.query('add_currency_to_all_users', [currency_key, tg_chat_id, amount])

    async def add_currency_to_channel(self, currency_key: str, channel_id: int, amount: int):
        return await self.query('add_currency_to_channel', [currency_key, channel_id, amount])

    async def get_user_currency_amount(self, currency_key: str, user_id: int):
        return await self.query('get_user_currency', [currency_key, user_id])

    async def get_list_value_custom(self, list_name, field)->List:
        list = await self.get_list_values_full(list_name)
        output = []

        for list_value in list:
            if list_value[field] is not None:
                output.append(list_value[field])

        return output

    async def get_list_values_str(self, list_name)->List[str]:
        return await self.get_list_value_custom(list_name, 'value_str')

    async def get_list_values_int(self, list_name) -> List[int]:
        return await self.get_list_value_custom(list_name, 'value_int')

    async def get_list_values_dec(self, list_name) -> List[float]:
        return await self.get_list_value_custom(list_name, 'value_dec')

    async def add_to_list(self, list_name, val_str, val_int, val_dec):
        await self.query('save_to_list', [list_name, val_str, val_int, val_dec])

    ### DB METHODS WITH CACHE ###

    # Force means skip cache
    async def get_auth_subchat(self, tg_chat_id: int, skip_cache: bool=False):
        cache_key = redis_key.get_tg_auth_channel_key(tg_chat_id)
        data = None

        if not skip_cache:
            data = await self.redis.get_parsed_value_by_key(cache_key)

        if data is None:
            data = await self.getSubchatWithAuth(tg_chat_id)
            if len(data) > 0:
                await self.redis.set_parsed_value_by_key(cache_key, data[0], redis_key.ttl_day)

        return data

    async def get_auth_subchats(self):
        channels = await self.getTgChatAvailChannelsWithAuth()

        for channel in channels:
            cache_key = redis_key.get_tg_auth_channel_key(channel['tg_chat_id'])
            await self.redis.set_parsed_value_by_key(cache_key, channel, redis_key.ttl_day)

        return channels

    async def get_global_events(self, skip_cache=False):
        cache_key = redis_key.get_global_events()
        data = None

        if not skip_cache:
            data = await self.redis.get_parsed_value_by_key(cache_key)

        if data is None:
            data = await self.query('get_active_global_events', [])
            if len(data) > 0:
                await self.redis.set_parsed_value_by_key(cache_key, data, redis_key.ttl_day)

        return data

    async def get_stream_flows(self, tw_id):
        cache_list = redis_key.get_tw_channel_stream_flow(tw_id)

        return await self.redis.get_parsed_list_members(cache_list)

    async def add_stream_flow(self, tw_id, flow_data):
        cache_list = redis_key.get_tw_channel_stream_flow(tw_id)

        await self.redis.add_to_list_parsed(cache_list, flow_data, redis_key.ttl_day)

    async def get_tg_chat_special_rights(self, channel_id):
        cache_list = redis_key.get_tg_chat_rights(channel_id=channel_id)
        return await self.redis.get_parsed_list_members(cache_list)

    async def get_all_tg_chat_special_rights(self, channel_id=None):
        if channel_id is None:
            rights = await self.query('get_all_tg_special_rights', [])
            pattern = redis_key.get_tg_chat_rights('*')
            await self.redis.delete_by_pattern(pattern)
        else:
            rights = await self.query('get_tg_chat_rights', [channel_id])
            pattern = redis_key.get_tg_chat_rights(channel_id)
            await self.redis.delete(pattern)

        for right in rights:
            cache_key = redis_key.get_tg_chat_rights(right['channel_id'])
            await self.redis.add_to_list_parsed(cache_key, right)

        return rights

    async def is_cooldown_getter(self, tg_chat_id)->bool:
        cache_key = redis_key.get_tg_cd_getter(tg_chat_id)
        exists = await self.redis.key_exists(cache_key)

        if exists is None:
            return False

        return bool(exists)

    async def set_getter_cooldown(self, tg_chat_id, seconds=30):
        cache_key = redis_key.get_tg_cd_getter(tg_chat_id)
        await self.redis.set_value_by_key(key=cache_key, val=tg_chat_id, expire=seconds)

    async def is_global_event_cooldown(self, tg_chat_id, tg_user_id, event_key)->bool:
        cache_key = 'tg.global.event.{}.{}.{}'.format(event_key, tg_chat_id, tg_user_id)
        exists = await self.redis.key_exists(cache_key)

        if exists is None:
            return False

        return bool(exists)

    async def set_global_event_cooldown(self, tg_chat_id, tg_user_id, event_key, seconds=30):
        cache_key = 'tg.global.event.{}.{}.{}'.format(event_key, tg_chat_id, tg_user_id)
        await self.redis.set_value_by_key(key=cache_key, val=tg_chat_id, expire=seconds)

    async def is_cooldown_non_verified_list(self, tg_chat_id) -> bool:
        cache_key = redis_key.get_tg_cd_non_verified_list(tg_chat_id)
        exists = await self.redis.key_exists(cache_key)

        if exists is None:
            return False

        return bool(exists)

    async def set_non_verified_list_cooldown(self, tg_chat_id, seconds=30):
        cache_key = redis_key.get_tg_cd_non_verified_list(tg_chat_id)
        await self.redis.set_value_by_key(key=cache_key, val=tg_chat_id, expire=seconds)

    async def is_cooldown_whoami(self, tg_chat_id, tg_user_id) -> bool:
        cache_key = redis_key.get_tg_cd_whoami(tg_chat_id, tg_user_id)
        exists = await self.redis.key_exists(cache_key)

        if exists is None:
            return False

        return bool(exists)

    async def set_whoami_cooldown(self, tg_chat_id, tg_user_id, seconds=60):
        cache_key = redis_key.get_tg_cd_whoami(tg_chat_id, tg_user_id)
        await self.redis.set_value_by_key(key=cache_key, val=tg_chat_id, expire=seconds)

    async def is_cooldown_inventory(self, tg_chat_id, tg_user_id) -> bool:
        cache_key = redis_key.get_tg_cd_inventory(tg_chat_id, tg_user_id)
        exists = await self.redis.key_exists(cache_key)

        if exists is None:
            return False

        return bool(exists)

    async def set_inventory_cooldown(self, tg_chat_id, tg_user_id, seconds=60):
        cache_key = redis_key.get_tg_cd_inventory(tg_chat_id, tg_user_id)
        await self.redis.set_value_by_key(key=cache_key, val=tg_chat_id, expire=seconds)

    async def is_cooldown_helloween_chestbox(self, tg_user_id) -> bool:
        cache_key = redis_key.get_tg_cd_halloween_chestbox(tg_user_id)
        exists = await self.redis.key_exists(cache_key)
        if exists is None:
            return False

        return bool(exists)

    async def set_helloween_chestbox_cooldown(self, tg_user_id, seconds=15):
        cache_key = redis_key.get_tg_cd_halloween_chestbox(tg_user_id)
        await self.redis.set_value_by_key(key=cache_key, val=tg_user_id, expire=seconds)

    async def update_tg_stats_message(self, tg_chat_id):
        key = redis_key.get_stats_tg_msg(tg_chat_id)
        await self.redis.get_next_index(key)

    async def update_tg_stats_kick(self, tg_chat_id):
        key = redis_key.get_stats_tg_kick(tg_chat_id)
        await self.redis.get_next_index(key)

    async def update_tg_stats_join(self, tg_chat_id):
        key = redis_key.get_stats_tg_join(tg_chat_id)
        await self.redis.get_next_index(key)

    async def get_tg_stats_msg(self, tg_chat_id, n=None):
        return await self.redis.get_value_by_key(redis_key.get_stats_tg_msg(tg_chat_id, n=n))

    async def get_tg_stats_kick(self, tg_chat_id, n=None):
        return await self.redis.get_value_by_key(redis_key.get_stats_tg_kick(tg_chat_id, n=n))

    async def get_tg_stats_join(self, tg_chat_id, n=None):
        return await self.redis.get_value_by_key(redis_key.get_stats_tg_join(tg_chat_id, n=n))

    async def get_tg_stats_from_cache(self, tg_chat_id, dt=None):
        msgs = await self.get_tg_stats_msg(tg_chat_id, n=dt)
        kicks = await self.get_tg_stats_kick(tg_chat_id, n=dt)
        joins = await self.get_tg_stats_join(tg_chat_id, n=dt)

        if msgs is None:
            msgs = 0

        if kicks is None:
            kicks = 0

        if joins is None:
            joins = 0

        return {"kick": kicks, "join": joins, "message": msgs}

    # Wrappers
    async def save_tg_stats_msg(self, channel_id, when_dt, counter):
        return await self.query('save_tg_stats', [channel_id, 'message', counter, when_dt])

    async def save_tg_stats_join(self, channel_id, when_dt, counter):
        return await self.query('save_tg_stats', [channel_id, 'kick', counter, when_dt])

    async def save_tg_stats_kick(self, channel_id, when_dt, counter):
        return await self.query('save_tg_stats', [channel_id, 'join', counter, when_dt])

    async def save_tg_stats_sub(self, channel_id, when_dt, counter):
        return await self.query('save_tg_stats', [channel_id, 'sub', counter, when_dt])

    async def save_tg_stats_nonsub(self, channel_id, when_dt, counter):
        return await self.query('save_tg_stats', [channel_id, 'nonsub', counter, when_dt])

    async def save_tg_stats_total(self, channel_id, when_dt, counter):
        return await self.query('save_tg_stats', [channel_id, 'total', counter, when_dt])

    async def save_tg_stats_nonverified(self, channel_id, when_dt, counter):
        return await self.query('save_tg_stats', [channel_id, 'nonverified', counter, when_dt])

    async def save_tg_stats_wls(self, channel_id, when_dt, counter):
        return await self.query('save_tg_stats', [channel_id, 'wls', counter, when_dt])

    async def save_tg_stats_bls(self, channel_id, when_dt, counter):
        return await self.query('save_tg_stats', [channel_id, 'bls', counter, when_dt])

    async def save_tg_stats_bots(self, channel_id, when_dt, counter):
        return await self.query('save_tg_stats', [channel_id, 'bots', counter, when_dt])

    async def save_twitch_sub_count_to_cache(self, tw_channel_id, tw_user_id, count):
        await self.redis.set_value_by_key(redis_key.get_tw_sub_month(tw_chat_id=tw_channel_id, tw_user_id=tw_user_id), count, expire=redis_key.ttl_week * 2)

    async def get_twitch_sub_count_from_cache(self, tw_channel_id, tw_user_id):
        return await self.redis.get_value_by_key(redis_key.get_tw_sub_month(tw_chat_id=tw_channel_id, tw_user_id=tw_user_id))

    async def get_telegram_group_size_from_cache(self, tg_channel_id: int):
        return await self.redis.get_value_by_key(redis_key.get_telegram_group_size(tg_channel_id))

    async def save_telegram_group_size_to_cache(self, tg_channel_id: int, size: int):
        return await self.redis.set_value_by_key(redis_key.get_telegram_group_size(tg_channel_id), int(size), expire=redis_key.ttl_day)

    async def get_winter_generator_details(self):
        return await self.redis.get_parsed_value_by_key(key='tg.winter.event')

    async def set_winter_generator_details(self, data):
        await self.redis.set_parsed_value_by_key(key='tg.winter.event', val=data, expire=redis_key.ttl_week)

