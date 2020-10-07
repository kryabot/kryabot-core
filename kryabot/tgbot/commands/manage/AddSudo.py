from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand
from tgbot.commands.common.special_rights import add_special_right


class AddSudo(BaseCommand):
    command_names = ['addsudo']
    access_level = UserAccess.CHAT_OWNER

    def __init__(self, event, parsed):
        super().__init__(event, parsed, AddSudo.access_level)
        self.must_be_reply = True

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return

        if not await self.is_chatadmin(self.reply_message.sender_id):
            await self.reply_fail(self.get_translation('CMD_ADDSUDO_NOT_ADMIN'))
            return

        await add_special_right('SUDO', self)
