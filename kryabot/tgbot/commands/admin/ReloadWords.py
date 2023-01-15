from tgbot.commands.base import BaseCommand


class ReloadWords(BaseCommand):
    def __init__(self, event, parsed, min_level):
        super().__init__(event, parsed, min_level)
        self.command_name = 'reloadwords'

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return

        await self.client.init_moderation()
        await self.reply_success()
