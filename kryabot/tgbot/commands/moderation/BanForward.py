from tgbot.commands.base import BaseCommand


class BanForward(BaseCommand):
    def __init__(self, event, parsed, min_level):
        super().__init__(event, parsed, min_level)
        self.command_name = 'banforward'
        self.must_be_reply = True

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return
