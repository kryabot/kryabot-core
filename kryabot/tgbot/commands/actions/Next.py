from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand
from utils.date_diff import get_datetime_diff_text
from datetime import datetime, timedelta


class Next(BaseCommand):
    command_names = ['next']
    access_level = UserAccess.CHAT_ADMIN

    def __init__(self, event, parsed):
        super().__init__(event, parsed, Next.access_level)

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return

        if self.channel['kick_mode'] != 'PERIOD' or self.channel['auto_mass_kick'] is None or self.channel['auto_mass_kick'] == 0:
            await self.event.reply(self.get_translation('CMD_NEXT_OFF'))
            return

        if (self.channel['last_auto_kick'] + timedelta(days=self.channel['auto_mass_kick'])) <= datetime.now():
            await self.event.reply(self.get_translation('CMD_NEXT_NOW'))
            return

        text = await get_datetime_diff_text(self.channel['last_auto_kick'] + timedelta(days=self.channel['auto_mass_kick']), datetime.now())

        if text is not None and len(text) > 0:
            await self.event.reply('{nexttext} {remaining} :3'.format(remaining=text, nexttext=self.get_translation('CMD_NEXT_IN')))
            return

        await self.event.reply(self.get_translation('CMD_NEXT_NOW'))
