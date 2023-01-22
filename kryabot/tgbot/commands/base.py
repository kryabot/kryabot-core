from typing import List

from telethon.tl.types import InputMediaDocument, InputMediaPhoto, InputPhoto, InputDocument
from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.common.media import get_media_info

# TODO: cache?
from utils.constants import TG_TEST_GROUP_ID

super_admin_list = [766888597]


def xstr(s):
    if s is None:
        return ''
    else:
        return str(s)


class BaseCommand:
    command_names = []

    def __init__(self, event, parsed, min_level=UserAccess.UNKNOWN):
        self.parsed = parsed
        self.event = event
        self.client = event.client
        self.translator = event.client.translator
        self.logger = event.client.logger
        self.db = event.client.db
        self.user = None
        self.channel = None
        self.sender = None
        self.chat = None
        self.min_level: UserAccess = min_level
        self.user_level: List[UserAccess] = [UserAccess.UNKNOWN]
        self.admins = []
        self.bot_lang = 'en'
        self.must_be_reply = False
        self.must_be_forward = False
        self.need_admin_rights = False
        self.reply_message = None
        self.forward_message = None
        self.test_only: bool = False

    async def get_text_after_command(self):
        try:
            return ' '.join(self.parsed.values())
        except:
            return ''

    async def validate(self):
        pass

    async def get_first(self, array):
        try:
            return array[0]
        except:
            if array is None or array == [] or array == ():
                return None
            return array

    async def fill_user_rights(self):
        if self.sender is None or self.sender == [] or self.sender == {}:
            self.user_level.append(UserAccess.NOT_VERIFIED)
        else:
            self.user_level.append(UserAccess.VERIFIED)

        if self.event.message.sender_id in super_admin_list:
            self.user_level.append(UserAccess.SUPER_ADMIN)
        if self.sender['user_id'] == self.channel['user_id']:
            self.user_level.append(UserAccess.CHAT_OWNER)
        if await self.is_chatsudo(self.sender['user_id'], self.event.message.sender_id):
            self.user_level.append(UserAccess.CHAT_SUDO)
        if await self.is_chatadmin(self.event.message.sender_id):
            self.user_level.append(UserAccess.CHAT_ADMIN)

        # TODO: follow and sub flags (from cache, not from api!)

    async def fetch_data(self):
        self.chat = await self.event.get_input_chat()
        self.channel = await self.get_first(await self.client.db.get_auth_subchat(self.event.message.to_id.channel_id))
        self.sender = await self.get_first(await self.client.db.getUserByTgChatId(self.event.message.sender_id))
        self.admins = await self.client.get_group_admins_cache(self.chat)
        await self.fill_user_rights()

        if self.channel is not None:
            self.bot_lang = self.channel['bot_lang']

        if self.must_be_reply:
            self.reply_message = await self.event.message.get_reply_message()

    def get_translation(self, key):
        return self.translator.getLangTranslation(self.bot_lang, key)

    async def can_process(self)->bool:
        self.logger.info("Command: {}, required right: {}, user {} got rights {}".format(self.__class__, self.min_level, self.sender['user_id'], self.user_level))
        if self.channel is None:
            return False

        if self.test_only and not self.is_test_group():
            return False

        if self.min_level not in self.user_level:
            return False

        if self.channel['auth_status'] == 0:
            await self.reply_fail(self.get_translation('GENERAL_MISSING_AUTH'))
            return False

        if self.channel['force_pause'] == 1:
            await self.reply_fail(self.get_translation('GENERAL_TG_GROUP_MISSCONFIGURED'))
            return False

        if self.must_be_reply and not self.event.message.is_reply:
            await self.reply_fail(self.get_translation('CMD_NOT_REPLY'))
            return False

        return True

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return

        await self.event.reply('This is base command!')

    async def is_superadmin(self, tg_user_id=None):
        if tg_user_id is None:
            return self.user_level == UserAccess.SUPER_ADMIN

        return tg_user_id in super_admin_list

    async def is_chatadmin(self, tg_user_id=None):
        if tg_user_id is None:
            any_of = [UserAccess.CHAT_ADMIN, UserAccess.CHAT_SUDO, UserAccess.CHAT_OWNER, UserAccess.SUPER_ADMIN]
            return len(set(self.user_level).intersection(any_of)) > 0

        for admin in self.admins:
            if admin.id == tg_user_id:
                return True

        return False

    async def is_blacklisted(self, kb_id, tg_id)->bool:
        return bool(await self.client.is_blacklisted(kb_user_id=kb_id, tg_user_id=tg_id, channel=self.channel))

    async def is_whitelisted(self, kb_id, tg_id)->bool:
        return bool(await self.client.is_whitelisted(kb_user_id=kb_id, tg_user_id=tg_id, channel=self.channel))

    async def is_chatsudo(self, kb_id, tg_id)->bool:
        return bool(await self.client.is_chatsudo(kb_user_id=kb_id, tg_user_id=tg_id, channel=self.channel))

    async def get_media_info(self, media=None):
        if media is None:
            media = self.event.media

        return await get_media_info(media)

    async def create_media(self, message_type, message_id, message_hash, file_ref):
        if message_type == 'MessageMediaDocument':
            return InputMediaDocument(id=InputDocument(id=int(message_id), access_hash=int(message_hash), file_reference=file_ref))
        if message_type == 'MessageMediaPhoto':
            return InputMediaPhoto(id=InputPhoto(id=int(message_id), access_hash=int(message_hash), file_reference=file_ref))
        if message_type == 'MessageMediaGeoLive':
            pass
        if message_type == 'MessageMediaPoll':
            pass

        return None

    async def format_html_user_mention(self, tg_user):
        label = xstr(tg_user.username)
        if label is None or label == '':
            label = '{} {}'.format(xstr(tg_user.first_name), xstr(tg_user.last_name))

        return '<a href="tg://user?id={id}">{lb}</a>'.format(id=tg_user.id, lb=label.strip())

    async def reply_success(self, text=''):
        if len(text) > 0:
            await self.event.reply('✅ {}'.format(text))
        else:
            await self.event.reply('✅')

    async def reply_fail(self, text=''):
        if len(text) > 0:
            await self.event.reply('⚠️ {}'.format(text))
        else:
            await self.event.reply('⚠️')

    async def reply_incorrect_input(self):
        await self.reply_fail(self.get_translation('CMD_INCORRECT_INPUT'))

    def is_test_group(self):
        return self.channel['tg_chat_id'] == TG_TEST_GROUP_ID
