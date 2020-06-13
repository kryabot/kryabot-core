from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand


class VoteHelp(BaseCommand):
    command_names = ['votehelp']
    access_level = UserAccess.CHAT_ADMIN

    def __init__(self, event, parsed):
        super().__init__(event, parsed, VoteHelp.access_level)

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return

        await self.event.reply(self.get_translation('HELP_USER_VOTES'))
