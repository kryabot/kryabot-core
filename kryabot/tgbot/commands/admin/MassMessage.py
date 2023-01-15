from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand
from tgbot.events.utils import is_valid_channel


class MassMessage(BaseCommand):
    command_names = ['massmessage']
    access_level = UserAccess.SUPER_ADMIN

    def __init__(self, event, parsed):
        super().__init__(event, parsed, MassMessage.access_level)
        self.must_be_reply = True

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return

        chats = await self.db.get_auth_subchats()
        i = 0

        for chat in chats:
            try:
                if not is_valid_channel(chat):
                    continue

                await self.client.send_message(chat['tg_chat_id'], self.reply_message)
                i = i + 1
            except Exception as e:
                await self.client.exception_reporter(e, 'Tried to send mass message to chat {} {}'.format(chat['tg_chat_id'], chat['channel_name']))

        await self.reply_success(self.get_translation('MASS_MESSAGE_SENT').format(i=i))
