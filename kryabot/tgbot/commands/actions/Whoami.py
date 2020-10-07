from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand
from tgbot.commands.common.user_data import get_user_data, format_user_data


class Whoami(BaseCommand):
    command_names = ['whoami', 'who']
    access_level = UserAccess.NOT_VERIFIED

    def __init__(self, event, parsed):
        super().__init__(event, parsed, Whoami.access_level)

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return

        if await self.db.is_cooldown_whoami(self.channel['tg_chat_id'], self.event.sender_id):
            return

        data = await get_user_data(self.client, self.channel, self.event.sender_id, skip_bits=False)
        if data['is_verified'] is True:
            await self.db.set_whoami_cooldown(self.channel['tg_chat_id'], self.event.sender_id)

        text = await format_user_data(data, self.client, self.channel)
        await self.event.reply(text, link_preview=False)
