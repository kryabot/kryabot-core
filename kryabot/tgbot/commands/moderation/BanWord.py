from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand


class BanWord(BaseCommand):
    command_names = ['banword']
    access_level = UserAccess.CHAT_ADMIN

    def __init__(self, event, parsed):
        super().__init__(event, parsed, BanWord.access_level)

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return

        try:
            text = await self.get_text_after_command()
        except:
            text = ''

        if text is None or text == '':
            await self.reply_fail(self.get_translation('CMD_INCORRECT_INPUT'))
            return

        if self.channel['channel_subchat_id'] in self.client.moderation.word_list:
            for word in self.client.moderation.word_list[self.channel['channel_subchat_id']]:
                if word['word'].lower == text.lower:
                    await self.reply_fail(self.get_translation('CMD_BAN_WORD_EXISTS'))
                    return

        await self.db.addTgWord(self.channel['channel_subchat_id'], 1, text, self.sender['user_id'])
        await self.reply_success(self.get_translation('CMD_BAN_WORD_SUCCESS'))
        await self.client.init_moderation()
