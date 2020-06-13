from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand


class ReminderHelp(BaseCommand):
    command_names = ['reminderhelp']
    access_level = UserAccess.CHAT_ADMIN

    def __init__(self, event, parsed):
        super().__init__(event, parsed, ReminderHelp.access_level)

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return

        reply_text = self.translator.getLangTranslation(self.channel['bot_lang'], 'HELP_REMINDER')
        reply_text += '\n\n'
        reply_text += self.translator.getLangTranslation(self.channel['bot_lang'], 'REMINDER_CURRENT_CD').format(currentcd=self.channel['reminder_cooldown'])
        await self.event.reply(reply_text)