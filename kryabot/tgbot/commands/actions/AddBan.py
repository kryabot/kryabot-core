from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand
from tgbot.commands.common.special_rights import add_special_right


class AddBan(BaseCommand):
    command_names = ['addban']
    access_level = UserAccess.CHAT_ADMIN

    def __init__(self, event, parsed):
        super().__init__(event, parsed, AddBan.access_level)
        self.must_be_reply = True

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return

        if await self.is_chatadmin(self.reply_message.from_id):
            await self.reply_fail(self.get_translation('CMD_ADDBAN_IS_ADMIN'))
            return

        await add_special_right('BL', self)
