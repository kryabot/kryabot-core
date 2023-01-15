from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand
from tgbot.events.utils import is_valid_channel


class MessageOwners(BaseCommand):
    command_names = ['messageowners']
    access_level = UserAccess.SUPER_ADMIN

    def __init__(self, event, parsed):
        super().__init__(event, parsed, MessageOwners.access_level)
        self.must_be_reply = True

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return

        users = await self.db.do_query("SELECT channel.*, response.*  FROM channel LEFT JOIN request on request.user_id = channel.user_id LEFT JOIN response ON response.request_id = request.request_id LEFT JOIN  auth on auth.user_id = channel.user_id and auth.type = 'BOT';", [])
        i = 0

        if not self.reply_message:
            await self.reply_incorrect_input()
            return

        for user in users:
            try:
                if not user['request_id']:
                    continue

                if int(user['user_id']) != 4673:
                    continue

                if self.reply_message.media:
                    await self.reply_fail('Media not supported!')
                    continue
                else:
                    text: str = self.reply_message.raw_text
                    text = text.replace('TARGET_USER', user['channel_name'])

                    await self.client.send_message(int(user['tg_id']), text, link_preview=False)
                    i = i + 1
            except Exception as e:
                await self.client.exception_reporter(e, 'Tried to send mass message to chat {}'.format(user))

        await self.reply_success(self.get_translation('MASS_MESSAGE_SENT').format(i=i))
