from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand


class ReloadTranslations(BaseCommand):
    command_names = ['reloadtranslations']
    access_level = UserAccess.SUPER_ADMIN

    def __init__(self, event, parsed):
        super().__init__(event, parsed, ReloadTranslations.access_level)

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return

        await self.client.init_translation()
        await self.reply_success()
