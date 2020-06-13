from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand


class AddWarn(BaseCommand):
    command_names = ['addwarn']
    access_level = UserAccess.CHAT_ADMIN

    def __init__(self, event, parsed):
        super().__init__(event, parsed, AddWarn.access_level)
        self.must_be_reply = True

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return

        await self.client.moderation.add_warn(self.channel, self.reply_message, is_auto=False)
