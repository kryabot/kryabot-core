from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand


class SetLang(BaseCommand):
    command_names = ['setlang']
    access_level = UserAccess.CHAT_SUDO

    def __init__(self, event, parsed):
        super().__init__(event, parsed, SetLang.access_level)

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return

        try:
            new_lang = self.parsed.pop(1).lower()
        except:
            await self.reply_fail(self.get_translation('CMD_INCORRECT_INPUT'))
            return

        available_langs = ['en', 'ru']

        if new_lang not in available_langs:
            await self.reply_fail(self.get_translation('CMD_LANG_UNKNOWN').format(lang_new=new_lang))
            return

        if new_lang == self.channel['bot_lang']:
            await self.event.reply(self.get_translation('CMD_LANG_EXISTS').format(lang_new=new_lang))
            return

        await self.db.sebBotLang(self.channel['channel_subchat_id'], new_lang)
        await self.client.db.get_auth_subchat(self.channel['tg_chat_id'], skip_cache=True)
        await self.reply_success(self.get_translation('CMD_LANG_CHANGED').format(lang_old=self.channel['bot_lang'], lang_new=new_lang))
