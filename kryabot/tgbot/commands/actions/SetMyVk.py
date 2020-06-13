from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand
import re


class SetMyVk(BaseCommand):
    command_names = ['setmyvk']
    access_level = UserAccess.VERIFIED

    def __init__(self, event, parsed):
        super().__init__(event, parsed, SetMyVk.access_level)

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return

        try:
            text = await self.get_text_after_command()
            if len(text) > 0:
                text = text.replace('https://www.', '')
                text = text.replace('http://www.', '')
                text = text.replace('https://', '')
                text = text.replace('http://', '')

                split_text = text.split('/')
                vk_username = split_text[1].split('?')[0]

                new_text = 'https://vk.com/{}'.format(vk_username)
            else:
                new_text = ''
        except:
            await self.reply_fail(self.get_translation('CMD_SOC_INCORRECT_URL'))
            return

        await self.db.setUserSocVk(self.sender['user_id'], new_text)
        await self.db.getUserByTgChatId(self.event.message.from_id, skip_cache=True)
        await self.reply_success('OK!')
