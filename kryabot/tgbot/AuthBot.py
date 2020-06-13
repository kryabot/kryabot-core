from telethon import TelegramClient
from telethon import events
from telethon.errors import UserIsBlockedError
from telethon.tl.custom import Button
from telethon.extensions import html
from object.Database import Database
from object.BotConfig import BotConfig
from object.ApiHelper import ApiHelper
from object.Translator import Translator
from utils.twitch import get_active_oauth_data
import logging
import base64
import asyncio
import os
import traceback
from datetime import datetime, timedelta
from urllib import parse

monitoring_id = 1255287898
super_admins = [766888597]


@events.register(events.NewMessage(pattern='/ping'))
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


@events.register(events.NewMessage(pattern='/reloadtranslation', chats=[monitoring_id]))
async def reloadtranslations(event):
    await event.client.reload_translations()
    await event.reply('Done')


class AuthBot(TelegramClient):
    def __init__(self, loop=None, cfg=None):
        self.logger = logging.getLogger('krya.auth')
        self.logger.setLevel(logging.DEBUG)
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
        self.loop.create_task(self.ping_checker())

    async def run(self):
        await self.reload_translations()
        await self.start(bot_token=self.cfg.getTelegramConfig()['BOT_API_KEY'])
        self.me = await self.get_me()
        #await self.catch_up()
        #await self.run_until_disconnected()

    async def reload_translations(self):
        self.translator = Translator(await self.db.getTranslations(), self.logger)

    async def ping_checker(self):
        while True:
            await asyncio.sleep(3600)
            if self.last_ping + timedelta(hours=1) < datetime.now():
                await self.report_to_monitoring(' @Kuroskas missing ping from main bot!')
                # TODO: Autorestart KryaClient bot

    async def exception_reporter(self, err, info):
        await self.report_to_monitoring(message='Error: {}: {}\n\n{}\n\n<pre>{}</pre>'.format(type(err).__name__, err, info, ''.join(traceback.format_tb(err.__traceback__))))

    async def report_to_monitoring(self, message):
        await self.send_message(monitoring_id, message)

    async def process_start(self, event):
        sender = await event.get_sender()
        sender_string = '{} {} {} {}'.format(sender.id, sender.first_name, sender.last_name, sender.username)

        self.logger.info('{}: {}'.format(sender_string, event.raw_text))
        words = event.raw_text.split(' ')
        if len(words) != 2:
            await event.reply(self.format_translation('', '', 'AUTH_BAD_START'))
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
            return

        if params['code'] is None or params['code'] == '':
            self.logger.info('{}: {}'.format(sender_string, 'Hash has no code parameter'))
            await event.reply(self.format_translation('', '', 'AUTH_BAD_HASH'))
            return

        self.logger.info('Received code: ' + params['code'])
        # Check if tg chat already linked to any twitch account
        chatCheck = await self.db.getResponseByChatId(event.message.from_id)
        if len(chatCheck) == 0:
            # Check if request with this code exists. What to do if 1+ found?
            request = await self.db.selectExisingActiveRequestsByCode(params['code'])
            if len(request) != 1:
                self.logger.info('{}: {} {}'.format(sender_string, 'Unknown or ambig code', params['code']))
                await event.reply(self.format_translation('', '', 'AUTH_INACTIVE_CODE'))
                return

            # Check if response does not exists yet
            response = await self.db.getResponseByRequest(request[0]['request_id'])
            if len(response) == 0:
                user_entity = await self.get_entity(event.message.from_id)
                await self.db.createResponseRecord(request[0]['request_id'], str(event.message.from_id),
                                              str(user_entity.first_name),
                                              str(user_entity.last_name), str(user_entity.username))
            chatCheck = await self.db.getResponseByChatId(event.message.from_id)

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

        if currentChannel == None:
            await event.reply(self.format_translation(currentChannel['channel_name'], '', 'AUTH_NO_SUBCHAT'))
            self.logger.info('{}: {}'.format(sender_string, 'channel_no_subchat'))
            return

        requestor = await self.db.getUserByTgChatId(event.message.chat_id, skip_cache=True)

        if len(requestor) == 0:
            await event.reply(self.format_translation(currentChannel['channel_name'], '', 'AUTH_NOT_VERIFIED'))
            self.logger.info('{}: {}'.format(sender_string, 'user_not_verified'))
            return

        try:
            if requestor[0]['tw_id'] == 0:
                twitch_user_by_name = await self.api.twitch.get_user_by_name(requestor[0]['name'])
                await self.db.updateUserTwitchId(requestor[0]['user_id'], twitch_user_by_name['users'][0]['_id'])
                requestor[0]['tw_id'] = twitch_user_by_name['users'][0]['_id']
        except Exception as e:
            self.logger.error('Failed to upate tw_id for {uname}: {err}'.format(uname=requestor[0]['name'], err=str(e)))
            pass

        rights = await self.db.getUserRightsInChannel(currentChannel['channel_id'], requestor[0]['user_id'])
        is_banned = False
        is_vip = False

        if rights:
            for right in rights:
                if right['right_type'] == 'BLACKLIST':
                    is_banned = True
                if right['right_type'] == 'WHITELIST':
                    is_vip = True

        if is_banned:
            await event.reply(self.format_translation(currentChannel['channel_name'], '', 'AUTH_USER_BLACKLISTED'))
            self.logger.info('Result: user_blacklisted')
            return

        if (not is_vip) and currentChannel['join_follower_only'] == 1:
            try:
                follower_info = await self.api.twitch.check_channel_following(currentChannel['tw_id'], requestor[0]['tw_id'])
            except Exception as e:
                self.logger.error(str(e))
                if '404' in str(e):
                    await event.reply(self.format_translation(currentChannel['channel_name'], '', 'AUTH_NOT_FOLLOWER'))
                    self.logger.info('Result: not_follower, failed to follower status')
                    return
                else:
                    await event.reply(self.format_translation(currentChannel['channel_name'], requestor[0]['name'], 'AUTH_SYS_ERR'))
                    self.logger.info('Result: sys_err, failed to check sub status')
                    return

        if (not is_vip) and currentChannel['join_sub_only'] == 1:
            currentChannel = await self.refresh_channel(currentChannel)
            sub = await self.api.is_sub_v2(currentChannel, requestor[0], self.db)

            if sub is None:
                await event.reply(self.format_translation(currentChannel['channel_name'], requestor[0]['name'], 'AUTH_SYS_ERR'))
                self.logger.info('Result: sys_err, failed to check sub status')
                return

            if sub is False:
                await event.reply(self.format_translation(currentChannel['channel_name'], requestor[0]['name'], 'AUTH_NOT_SUB'))
                self.logger.info('Result: not_sub')
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
                    self.logger.info('Result: sub_low_months')
                    return

        try:
            twitch_user = await self.api.twitch.get_user_by_id(requestor[0]['tw_id'])
            twitch_display_name = twitch_user['display_name']
        except Exception as e:
            twitch_display_name = requestor[0]['name']

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

