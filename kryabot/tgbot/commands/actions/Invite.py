from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand


class Invite(BaseCommand):
    command_names = ['invite']
    access_level = UserAccess.UNKNOWN

    def __init__(self, event, parsed):
        super().__init__(event, parsed, Invite.access_level)

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return

        reply = "{text}:\nhttps://tg.krya.dev/{invitename}".format(invitename=self.channel['channel_name'],
                                                                         text=self.get_translation('CMD_INVITE'))

        await self.event.reply(reply, link_preview=False)
