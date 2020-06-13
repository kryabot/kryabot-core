from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand
import re


class SetMyInst(BaseCommand):
    command_names = ['setmyinstagram']
    access_level = UserAccess.VERIFIED

    def __init__(self, event, parsed):
        super().__init__(event, parsed, SetMyInst.access_level)

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return

        try:
            text = await self.get_text_after_command()
            if len(text) > 0:
                text = text.split(' ')[0]
                text = text.replace('https://www.', '')
                text = text.replace('http://www.', '')
                text = text.replace('https://', '')
                text = text.replace('http://', '')

                split_text = text.split('/')
                username = split_text[1].split('?')[0]

                new_text = 'https://instagram.com/{}'.format(username)
            else:
                new_text = ''
        except:
            await self.reply_fail(self.get_translation('CMD_SOC_INCORRECT_URL'))
            return

        await self.db.setUserSocInst(self.sender['user_id'], new_text)
        await self.db.getUserByTgChatId(self.event.message.from_id, skip_cache=True)
        await self.reply_success('OK!')
