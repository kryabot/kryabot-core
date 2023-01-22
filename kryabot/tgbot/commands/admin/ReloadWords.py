from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand


class ReloadWords(BaseCommand):
    command_names = ['reloadwords']
    access_level = UserAccess.SUPER_ADMIN

    def __init__(self, event, parsed):
        super().__init__(event, parsed, ReloadWords.access_level)

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return

        await self.client.init_moderation()
        await self.reply_success()
