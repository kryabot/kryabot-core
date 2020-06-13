from tgbot.commands.base import BaseCommand


class GetMessageDetails(BaseCommand):
    def __init__(self, event, parsed, min_level):
        super().__init__(event, parsed, min_level)
        self.command_name = 'getmessagedetails'
        self.must_be_reply = True

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return

        await self.reply_success('MessageID: {}'.format(self.reply_message.id))
