from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand


class NewUserReport(BaseCommand):
    command_names = ['newuserreport']
    access_level = UserAccess.SUPER_ADMIN

    def __init__(self, event, parsed):
        super().__init__(event, parsed, NewUserReport.access_level)

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return

        data = await self.client.get_group_participant_full_data(self.channel, need_follows=False)
        self.logger.info(data['summary'])
        self.logger.info(data['users'])
        await self.reply_success()
