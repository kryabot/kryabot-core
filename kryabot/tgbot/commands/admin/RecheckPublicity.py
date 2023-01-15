from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand


class RecheckPublicity(BaseCommand):
    command_names = ['recheckpublicity']
    access_level = UserAccess.SUPER_ADMIN

    def __init__(self, event, parsed):
        super().__init__(event, parsed, RecheckPublicity.access_level)

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return

        await self.client.task_check_chat_publicity(sleep=10)
        await self.reply_success()
