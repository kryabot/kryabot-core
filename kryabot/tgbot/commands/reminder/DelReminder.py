from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand
from tgbot.commands.common.reminders import find_reminder


class DelReminder(BaseCommand):
    command_names = ['delreminder']
    access_level = UserAccess.CHAT_ADMIN

    def __init__(self, event, parsed):
        super().__init__(event, parsed, DelReminder.access_level)

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return

        try:
            keyword = self.parsed.pop(1)
        except:
            await self.event.reply(self.get_translation('KB_NO_KEYWORD'))
            return

        reminder = await find_reminder(keyword, self)
        if reminder is None:
            await self.event.reply(self.get_translation('CMD_REMINDER_NOT_FOUND'))

        await self.db.deleteReminderById(self.channel['user_id'], reminder['reminder_id'])
        await self.event.reply(self.get_translation('CMD_REMINDER_DELETED').format(reminder_key=reminder['reminder_key']))
