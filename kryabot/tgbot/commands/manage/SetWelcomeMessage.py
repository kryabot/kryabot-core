from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand


class SetWelcomeMessage(BaseCommand):
    command_names = ['setwelcomemessage']
    access_level = UserAccess.CHAT_ADMIN

    def __init__(self, event, parsed):
        super().__init__(event, parsed, SetWelcomeMessage.access_level)
        self.must_be_reply = True

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return

        await self.db.setWelcomeMessageId(self.channel['tg_chat_id'], self.reply_message.id)
        await self.reply_success(self.get_translation('CMD_WELCOME_MSG_SUCCESS'))
