from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand
from utils.date_diff import get_datetime_diff_text
from datetime import datetime, timedelta


class MyWarns(BaseCommand):
    command_names = ['mywarns']
    access_level = UserAccess.VERIFIED

    def __init__(self, event, parsed):
        super().__init__(event, parsed, MyWarns.access_level)

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return

        warns = await self.client.moderation.get_user_existing_warns(self.channel, self.event.message.from_id)
        if warns is None or len(warns) == 0:
            await self.event.reply(self.get_translation('CMD_MY_WARNS_EMPTY'))
            return

        await self.event.reply(self.get_translation('CMD_MY_WARNS').format(count=len(warns)))
