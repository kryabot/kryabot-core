from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand


class EnableGlobalEvents(BaseCommand):
    command_names = ['enableglobalevents']
    access_level = UserAccess.CHAT_ADMIN

    def __init__(self, event, parsed):
        super().__init__(event, parsed, EnableGlobalEvents.access_level)

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return
        
        await self.client.db.enableGlobalEvents(self.channel['tg_chat_id'])
        await self.reply_success(self.get_translation('CMD_ENABLED_GLOBAL_EVENTS'))

