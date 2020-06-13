from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand
from tgbot.commands.common.reminders import reminder_format_message


class GetReminders(BaseCommand):
    command_names = ['getreminders']
    access_level = UserAccess.CHAT_ADMIN

    def __init__(self, event, parsed):
        super().__init__(event, parsed, GetReminders.access_level)

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return

        await reminder_format_message(self.event, self.client, self.channel, False)
