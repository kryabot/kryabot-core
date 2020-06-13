from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand


class ShowReport(BaseCommand):
    command_names = ['showreport']
    access_level = UserAccess.CHAT_SUDO

    def __init__(self, event, parsed):
        super().__init__(event, parsed, ShowReport.access_level)

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return

        await self.client.db.showSubchatReport(self.channel['tg_chat_id'])
        await self.reply_success(self.get_translation('CMD_SHOW_REPORT_SUCCESS'))
