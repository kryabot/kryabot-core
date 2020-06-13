from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand


class DisableGlobalEvents(BaseCommand):
    command_names = ['disableglobalevents']
    access_level = UserAccess.CHAT_ADMIN

    def __init__(self, event, parsed):
        super().__init__(event, parsed, DisableGlobalEvents.access_level)

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return
        
        await self.client.db.disableGlobalEvents(self.channel['tg_chat_id'])
        await self.reply_success(self.get_translation('CMD_DISABLED_GLOBAL_EVENTS'))

