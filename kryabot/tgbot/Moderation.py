import json
import logging
from datetime import datetime, timedelta

from telethon.tl.types import PeerChannel, PeerUser

from object.RedisHelper import RedisHelper
from tgbot.WordModeration import is_forbidden
from tgbot.commands.common.media import get_media_info
from utils.formatting import format_html_user_mention


class Moderation:
    def __init__(self, logger, queue, tg, cfg):
        self.logger: logging.Logger = logger
        self.warning_history = {}
        self.word_list = None
        self.queue = queue
        self.tg = tg
        self.test_time_limit = 3600 # 1h
        self.limit_ban = 3
        self.restrict_time = 300
        self.cfg = cfg
        self.rh = RedisHelper.get_instance()
        self.WARN_ROOT = 'tg.moderation.warns'
        self.datetime_string_format = '%Y-%m-%d %H:%M:%S'

    async def setWordList(self, words):
        self.word_list = {}
        for word in words:
            if word['channel_subchat_id'] not in self.word_list:
                self.word_list[word['channel_subchat_id']] = []

            wordAction = {'word': word['word'], 'type': word['restrict_type_id']}
            self.word_list[word['channel_subchat_id']].append(wordAction)

    async def modarateForbiddenWords(self, channel, message):
        if channel['max_warns'] is None or channel['max_warns'] == 0:
            # 0 means disabled warn functionality
            return

        if channel['channel_subchat_id'] not in self.word_list:
            # Channel has no restricted words
            return False

        for word in self.word_list[channel['channel_subchat_id']]:
            forbidden = await is_forbidden(word['word'].lower(), message.raw_text.lower())

            if forbidden > 0:
                self.logger.info('Found restricted word {rw} by rule {rulenum} in message: {msg}'.format(rw=word['word'], msg=message.raw_text, rulenum=forbidden))
                await self.add_warn(channel, message, is_auto=True, word=word['word'])
                return True

        return False

    async def get_user_existing_warns(self, channel, tg_user_id):
        existing_user_warnings = await self.cache_get_user_warns(channel['channel_subchat_id'], tg_user_id)
        if len(existing_user_warnings) > 0:
            existing_user_warnings = [warn for warn in existing_user_warnings if warn['ts'] > datetime.now() - timedelta(hours=channel['warn_expires_in'])]

        return existing_user_warnings

    async def add_warn(self, channel, message, is_auto=False, word=''):
        # 0 means disabled functionality
        if channel['max_warns'] is None or channel['max_warns'] == 0:
            return

        existing_user_warnings = await self.get_user_existing_warns(channel, message.sender_id)

        warn = {}
        warn['ts'] = datetime.now()
        warn['message_id'] = message.id
        warn['text'] = message.raw_text
        warn['media'] = message.media is not None
        warn['word'] = word
        warn['auto'] = is_auto
        existing_user_warnings.append(warn)

        # Warn or mute
        warn_count = len(existing_user_warnings)
        user = await self.tg.get_entity(PeerUser(message.sender_id))
        user_url = await format_html_user_mention(user)

        if warn_count >= channel['max_warns']:
            channel_entity = await self.tg.get_entity(PeerChannel(channel['tg_chat_id']))
            try:
                await self.tg.mute_user(channel_entity, user, channel['warn_mute_h'] * 60 * 60)
            except Exception as err:
                await self.tg.exception_reporter(err, 'Failed to mute {u} in subchat {sc}'.format(u=user_url, sc=channel['channel_name']))

            warning_text = self.tg.translator.getLangTranslation(channel['bot_lang'], 'WARNS_MUTED').format(user=user_url, restrict_time=channel['warn_mute_h'])
            existing_user_warnings = []
        else:
            if is_auto:
                warning_text = self.tg.translator.getLangTranslation(channel['bot_lang'], 'WARNS_ADDED_AUTO').format(
                    user=user_url, warns=warn_count, total=channel['max_warns'])
            else:
                warning_text = self.tg.translator.getLangTranslation(channel['bot_lang'], 'WARNS_ADDED_MANUAL').format(
                    user=user_url, warns=warn_count, total=channel['max_warns'])

        await self.cache_set_user_warns(channel['channel_subchat_id'], message.sender_id, existing_user_warnings, channel['warn_expires_in'] * 60 * 60)
        await self.tg.send_message(channel['tg_chat_id'], warning_text)

    async def cache_get_user_warns(self, chat_id, user_id):
        try:
            existing_warns = await self.rh.get_value_by_key('tg.warns:{chatid}:{userid}'.format(chatid=chat_id, userid=user_id))
            if existing_warns is None:
                return []

            datas = json.loads(existing_warns)
            for data in datas:
                data['ts'] = datetime.strptime(data['ts'], self.datetime_string_format)

            return datas
        except Exception as e:
            self.logger.exception(e)
            return []

    async def cache_set_user_warns(self, chat_id, user_id, warns, expire_after):
        for warn in warns:
            warn['ts'] = warn['ts'].strftime(self.datetime_string_format)

        data = json.dumps(warns)
        redis_key = 'tg.warns:{chatid}:{userid}'.format(chatid=chat_id, userid=user_id)
        await self.rh.set_value_by_key(redis_key, data, expire=expire_after)
        await self.rh.add_to_list(self.WARN_ROOT, redis_key)

    async def filter_words(self, channel, message):
        await self.modarateForbiddenWords(channel, message)

    async def filter_media(self, event, channel):
        media_id, media_type, access_hash, file_ref, file_mime, file_size = await get_media_info(event.media)
        if await event.client.is_media_banned(channel['channel_id'], media_id, media_type):
            await event.client.delete_messages(event.message.to_id.channel_id, event.message.id)
