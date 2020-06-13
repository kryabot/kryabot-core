from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand
from tgbot.events.image_filter import get_image_data


class ScanImage(BaseCommand):
    command_names = ['scanimage']
    access_level = UserAccess.CHAT_SUDO

    def __init__(self, event, parsed):
        super().__init__(event, parsed, ScanImage.access_level)
        self.must_be_reply = True

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return

        data = await get_image_data(self.client, self.reply_message)
        if data is None:
            return

        resp = data['responses'][0]['safeSearchAnnotation']
        reply = 'Adult content: {}'.format(resp['adult'])
        reply += '\nSpoof content: {}'.format(resp['spoof'])
        reply += '\nMedical content: {}'.format(resp['medical'])
        reply += '\nViolence content: {}'.format(resp['violence'])
        reply += '\nRacy content: {}'.format(resp['racy'])

        await self.event.reply(reply)




