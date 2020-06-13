from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand
from tgbot.commands.common.user_data import get_user_data, format_user_data


class Whois(BaseCommand):
    command_names = ['whois']
    access_level = UserAccess.CHAT_ADMIN

    def __init__(self, event, parsed):
        super().__init__(event, parsed, Whois.access_level)
        self.must_be_reply = True

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return

        data = await get_user_data(self.client, self.channel, self.reply_message.from_id, skip_bits=False)
        text = await format_user_data(data, self.client, self.channel)
        await self.event.reply(text, link_preview=False)
