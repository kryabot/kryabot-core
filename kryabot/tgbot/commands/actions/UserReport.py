from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand


class UserReport(BaseCommand):
    command_names = ['userreport']
    access_level = UserAccess.SUPER_ADMIN

    def __init__(self, event, parsed):
        super().__init__(event, parsed, UserReport.access_level)

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return

        await self.client.run_user_report(self.channel, manual=True)
