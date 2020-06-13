from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand
from tgbot.commands.common.work_mode import set_chat_mode_follow


class ChatModeFollow(BaseCommand):
    command_names = ['chatmodefollow']
    access_level = UserAccess.CHAT_SUDO

    def __init__(self, event, parsed):
        super().__init__(event, parsed, ChatModeFollow.access_level)

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return

        await set_chat_mode_follow(self)
