from telethon.tl.types import DocumentAttributeVideo

from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand
from api.coub import Coub

class DLCoub(BaseCommand):
    command_names = ['dlcoub']
    access_level = UserAccess.SUPER_ADMIN

    def __init__(self, event, parsed):
        super().__init__(event, parsed, DLCoub.access_level)

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return

        try:
            coub_url = self.parsed.pop(1).lower()
        except:
            await self.reply_fail(self.get_translation('CMD_INCORRECT_INPUT'))
            return

        coub_url = coub_url.replace('https://', '')
        coub_url = coub_url.replace('http://', '')

        if not coub_url.startswith('coub.com/view/') and not coub_url.startswith('www.coub.com/view/'):
            await self.reply_fail(self.get_translation('CMD_INCORRECT_INPUT'))
            return

        coub_url = "https://{}".format(coub_url)
        api = Coub(cfg=None)
        coub_media = await api.get_coub_io(coub_url)
        coub_media.name = "coub.mp4"
        await self.client.send_file(self.event.message.to_id.channel_id, file=coub_media, attributes=[DocumentAttributeVideo(w=1080, h=720, duration=0, supports_streaming=True)], supports_streaming=True)
