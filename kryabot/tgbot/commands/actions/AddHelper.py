from telethon.tl.functions.channels import InviteToChannelRequest
from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand


class AddHelper(BaseCommand):
    command_names = ['addhelper']
    access_level = UserAccess.CHAT_ADMIN

    def __init__(self, event, parsed):
        super().__init__(event, parsed, AddHelper.access_level)

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return

        await self.client(InviteToChannelRequest(self.event.message.to_id.channel_id, ['@KryaHelpBot']))