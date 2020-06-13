from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand
from tgbot.commands.common.chat_entrance import chat_entrance_disable


class ChatEntranceDisable(BaseCommand):
    command_names = ['invdisable']
    access_level = UserAccess.CHAT_SUDO

    def __init__(self, event, parsed):
        super().__init__(event, parsed, ChatEntranceDisable.access_level)

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return

        await chat_entrance_disable(self)
