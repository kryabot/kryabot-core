from telethon import TelegramClient
from telethon import events
from telethon.errors import UserIsBlockedError
from telethon.tl.custom import Button
from telethon.extensions import html
from object.Database import Database
from object.ApiHelper import ApiHelper
from object.Pinger import Pinger
from object.System import System
from object.Translator import Translator
from tgbot.constants import TG_GROUP_MONITORING_ID
from utils.twitch import get_active_oauth_data
import logging
import base64
import asyncio
import os
import traceback
from datetime import datetime
from urllib import parse


@events.register(events.NewMessage(pattern='/ping', chats=[TG_GROUP_MONITORING_ID]))
async def pong(event):
    event.client.last_ping = datetime.now()
    await event.reply('pong')


@events.register(events.NewMessage(pattern='\/start*', func=lambda e: e.is_private))
async def start(event):
    try:
        await event.client.process_start(event)
    except UserIsBlockedError as ex:
        pass
    except Exception as ex:
        await event.client.exception_reporter(ex, 'Start event')


@events.register(events.NewMessage(pattern='/reloadtranslation', chats=[TG_GROUP_MONITORING_ID]))
async def reloadtranslations(event):
    await event.client.reload_translations()
    await event.reply('Done')


class AuthBot(TelegramClient):
    def __init__(self, loop=None, cfg=None):
        self.logger = logging.getLogger('krya.auth')
        self.cfg = cfg
        self.db = Database(None, 2, cfg=self.cfg)
        self.api = ApiHelper(cfg=self.cfg, redis=self.db.redis)
        self.translator = None
        self.me = None
        self.last_ping = datetime.now()

        # Path to session file
        path = os.getenv('SECRET_DIR')
        if path is None:
            path = ''

        super().__init__(path + 'auth_bot_session', base_logger=self.logger, api_id= self.cfg.getTelegramConfig()['API_ID'], api_hash=self.cfg.getTelegramConfig()['API_HASH'])

        self.add_event_handler(pong)
        self.add_event_handler(start)
        self.add_event_handler(reloadtranslations)
        self._parse_mode = html
        self.loop.create_task(self.db.db_activity())
        self.loop.create_task(Pinger(System.AUTHBOT_TELEGRAM, self.logger, self.db.redis).run_task())

    async def run(self):
        await self.reload_translations()
        await self.start(bot_token=self.cfg.getTelegramConfig()['BOT_API_KEY'])
        self.me = await self.get_me()
        #await self.catch_up()
        #await self.run_until_disconnected()

    async def reload_translations(self):
        self.translator = Translator(await self.db.getTranslations(), self.logger)

    async def exception_reporter(self, err, info):
        await self.report_to_monitoring(message='Error: {}: {}\n\n{}\n\n<pre>{}</pre>'.format(type(err).__name__, err, info, ''.join(traceback.format_tb(err.__traceback__))))

    async def report_to_monitoring(self, message):
        await self.send_message(TG_GROUP_MONITORING_ID, message)

    async def process_start(self, event):
        sender = await event.get_sender()
        sender_string = '{} {} {} {}'.format(sender.id, sender.first_name, sender.last_name, sender.username)

        self.logger.info('{}: {}'.format(sender_string, event.raw_text))
        words = event.raw_text.split(' ')
        if len(words) != 2:
            await event.reply(self.format_translation('', '', 'AUTH_BAD_START'))
            self.logger.info('Result: start_empty')
            return

        val = words[1]
        if len(val) % 4 != 0:
            val += ('===')[0: 4 - (len(val) % 4)]

        input_data = val
        try:
            input_data = base64.b64decode(val).decode()
            params = dict(parse.parse_qsl(input_data))
        except Exception as e:
            await event.reply(self.format_translation('', '', 'AUTH_BAD_HASH'))
            self.logger.error('Decode failed for: ' + str(input_data) + ' error: ' + str(e))
            self.logger.info('Result: start_failed_parse')
            return

        if 'code' not in params or params['code'] is None or params['code'] == '':
            self.logger.info('{}: {}'.format(sender_string, 'Hash has no code parameter'))
            await event.reply(self.format_translation('', '', 'AUTH_BAD_HASH'))
            self.logger.info('Result: start_failed_parse')
            return

        if 'id' not in params or params['id'] is None or params['id'] == '':
            self.logger.info('{}: {}'.format(sender_string, 'Hash has no id parameter'))
            await event.reply(self.format_translation('', '', 'AUTH_BAD_HASH'))
            self.logger.info('Result: start_failed_parse')
            return

        self.logger.info('Received code: ' + params['code'])
        # Check if tg chat already linked to any twitch account
        chatCheck = await self.db.getResponseByChatId(event.message.sender_id)
        if len(chatCheck) == 0:
            # Check if request with this code exists. What to do if 1+ found?
            request = await self.db.selectExisingActiveRequestsByCode(params['code'])
            if len(request) != 1:
                self.logger.info('{}: {} {}'.format(sender_string, 'Unknown or ambig code', params['code']))
                await event.reply(self.format_translation('', '', 'AUTH_INACTIVE_CODE'))
                self.logger.info('Result: start_duplicate')
                return

            # Check if response does not exists yet
            response = await self.db.getResponseByRequest(request[0]['request_id'])
            if len(response) == 0:
                user_entity = await self.get_entity(event.message.sender_id)
                await self.db.createResponseRecord(request[0]['request_id'], str(event.message.sender_id),
                                              str(user_entity.first_name),
                                              str(user_entity.last_name), str(user_entity.username))
            chatCheck = await self.db.getResponseByChatId(event.message.sender_id)

        # Technical problems, records was not created.
        if len(chatCheck) == 0:
            await event.reply(self.format_translation('', '', 'AUTH_SYS_ERR'))
            self.logger.info('Result: sys_err, empty chatCheck')
            return

        availableChannels = await self.db.getTgChatAvailChannelsWithAuth()
        currentChannel = None
        for ch in availableChannels:
            if str(ch['channel_id']) == str(params['id']):
                currentChannel = ch

        if currentChannel is None:
            await event.reply(self.format_translation('', '', 'AUTH_NO_SUBCHAT'))
            self.logger.info('{}: {}'.format(sender_string, 'channel_no_subchat'))
            self.logger.info('Result: start_no_chat')
            return

        requestor = await self.db.getUserByTgChatId(event.message.chat_id, skip_cache=True)

        if len(requestor) == 0:
            await event.reply(self.format_translation(currentChannel['channel_name'], '', 'AUTH_NOT_VERIFIED'))
            self.logger.info('{}: {}'.format(sender_string, 'user_not_verified'))
            self.logger.info('Result: start_missing_link')
            return

        try:
            if requestor[0]['tw_id'] == 0:
                twitch_user_by_name = await self.api.twitch.get_users(usernames=[requestor[0]['name']], skip_cache=True)
                twitch_user_by_name = twitch_user_by_name['data'][0]
                await self.db.updateUserTwitchId(requestor[0]['user_id'], int(twitch_user_by_name['id']))
                requestor[0]['tw_id'] = int(twitch_user_by_name['id'])
        except Exception as e:
            self.logger.error('Failed to upate tw_id for {uname}: {err}'.format(uname=requestor[0]['name'], err=str(e)))
            pass

        rights = await self.db.getUserRightsInChannel(currentChannel['channel_id'], requestor[0]['user_id'])
        is_banned = False
        is_vip = False
        has_invitation = False
        skip_checks = False

        if rights:
            for right in rights:
                if right['right_type'] == 'BLACKLIST':
                    is_banned = True
                if right['right_type'] == 'WHITELIST':
                    is_vip = True

        if is_banned:
            await event.reply(self.format_translation(currentChannel['channel_name'], '', 'AUTH_USER_BLACKLISTED'))
            self.logger.info('Result: join_reject_blacklist')
            return

        invites = await self.db.getTgInvite(currentChannel['channel_id'], requestor[0]['user_id'])
        if invites and len(invites) > 0:
            has_invitation = True

        if is_vip or has_invitation:
            skip_checks = True

        if (not skip_checks) and currentChannel['enabled_join'] == 0:
            await event.reply(self.format_translation(currentChannel['channel_name'], '', 'AUTH_GROUP_CLOSED'))
            self.logger.info('Result: join_reject_closed')
            return

        if (not skip_checks) and currentChannel['join_follower_only'] == 1:
            try:
                follower_info = await self.api.twitch.check_channel_following(currentChannel['tw_id'], requestor[0]['tw_id'])
                if follower_info and 'data' in follower_info and len(follower_info['data']) > 0:
                    pass
                else:
                    await event.reply(self.format_translation(currentChannel['channel_name'], '', 'AUTH_NOT_FOLLOWER'))
                    self.logger.info('Result: join_reject_not_follower')
            except Exception as e:
                self.logger.error(str(e))
                await event.reply(self.format_translation(currentChannel['channel_name'], requestor[0]['name'], 'AUTH_SYS_ERR'))
                self.logger.info('Result: sys_err, failed to check follow status')
                return

        if (not skip_checks) and currentChannel['join_sub_only'] == 1:
            currentChannel = await self.refresh_channel(currentChannel)
            sub = await self.api.is_sub_v2(currentChannel, requestor[0], self.db)

            if sub is None:
                await event.reply(self.format_translation(currentChannel['channel_name'], requestor[0]['name'], 'AUTH_SYS_ERR'))
                self.logger.info('Result: sys_err, failed to check sub status')
                return

            if sub is False:
                await event.reply(self.format_translation(currentChannel['channel_name'], requestor[0]['name'], 'AUTH_NOT_SUB'))
                self.logger.info('Result: join_reject_not_sub')
                return

            if currentChannel['min_sub_months'] > 0:
                cache_info = await self.db.get_twitch_sub_count_from_cache(currentChannel['tw_id'], requestor[0]['tw_id'])
                if cache_info is not None:
                    if not isinstance(cache_info, int):
                        try:
                            cache_info = int(cache_info)
                        except:
                            cache_info = 0
                else:
                    cache_info = 0

                if cache_info < currentChannel['min_sub_months']:
                    await event.reply(self.format_translation(currentChannel['channel_name'], requestor[0]['name'], 'AUTH_SUB_LOW_MONTH'))
                    self.logger.info('Result: join_reject_low_sub_months')
                    return

        try:
            twitch_user = await self.api.twitch.get_users(ids=[requestor[0]['tw_id']])
            twitch_user = twitch_user['data'][0]
            twitch_display_name = twitch_user['display_name']
        except Exception as e:
            twitch_display_name = requestor[0]['dname'] if requestor[0]['dname'] is not None and len(requestor[0]['dname']) > 0 else requestor[0]['name']

        # Success
        reply = self.format_translation(currentChannel['channel_name'], twitch_display_name, 'AUTH_JOIN_SUCCESS')
        self.logger.info('Result: join_success')

        msg = await event.reply(message=reply, buttons=Button.url(currentChannel['channel_name'], 'tg://join?invite={link}'.format(link=currentChannel['join_link'])))
        await asyncio.sleep(300)
        await msg.delete()

    async def refresh_channel(self, channel):
        auth_data = await get_active_oauth_data(channel['user_id'], self.db, self.api)
        if auth_data is not None:
            channel['token'] = auth_data['token']
            channel['expires_at'] = auth_data['expires_at']
        return channel

    def format_translation(self, channel_name, user_name, key):
        raw = self.translator.getLangTranslation('ru', key)
        return raw.format(name=user_name, channel=channel_name)

