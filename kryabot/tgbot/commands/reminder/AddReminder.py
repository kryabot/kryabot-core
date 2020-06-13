from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand
from tgbot.commands.common.reminders import find_reminder


class AddReminder(BaseCommand):
    command_names = ['addreminder']
    access_level = UserAccess.CHAT_ADMIN

    def __init__(self, event, parsed):
        super().__init__(event, parsed, AddReminder.access_level)

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return

        try:
            keyword = self.parsed.pop(1)
        except:
            await self.event.reply(self.get_translation('KB_NO_KEYWORD'))
            return

        try:
            text = await self.get_text_after_command()
        except:
            text = ''

        if text is None or text == '':
            await self.event.reply(self.get_translation('CMD_REMINDER_MISSING_DESC'))
            return

        existing_reminder = await find_reminder(keyword, self)
        await self.db.saveReminderByUserId(self.channel['user_id'],
                                            0 if existing_reminder is None else existing_reminder['reminder_id'],
                                            keyword,
                                            text,
                                            False)

        if existing_reminder is None:
            await self.event.reply(self.get_translation('CMD_REMINDER_CREATED'))
        else:
            await self.event.reply(self.get_translation('CMD_REMINDER_UPDATED'))
