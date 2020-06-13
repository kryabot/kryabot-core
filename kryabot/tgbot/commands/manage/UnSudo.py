from telethon.tl.types import PeerUser

from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand
from utils.value_check import avoid_none


class UnSudo(BaseCommand):
    command_names = ['unsudo']
    access_level = UserAccess.CHAT_OWNER

    def __init__(self, event, parsed):
        super().__init__(event, parsed, UnSudo.access_level)
        self.must_be_reply = True

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return

        target_user = await self.client.get_entity(PeerUser(self.reply_message.from_id))
        admin_user = await self.client.get_entity(PeerUser(self.event.message.from_id))

        await self.client.report_to_monitoring(
            '[{chn}]\n User {afn} {aln} {au} {aid} removed special rights from user {tfn} {tln} {tu} {tid}'.format(
                chn=self.channel['channel_name'],
                afn=await avoid_none(admin_user.first_name),
                aln=await avoid_none(admin_user.last_name),
                au=await avoid_none(admin_user.username),
                aid=await avoid_none(self.event.message.from_id),
                tfn=await avoid_none(target_user.first_name),
                tln=await avoid_none(target_user.last_name),
                tu=await avoid_none(target_user.username),
                tid=await avoid_none(self.reply_message.from_id)
            ))

        await self.db.removeTgSudoRight(self.channel['channel_id'], self.reply_message.from_id)
        await self.client.init_special_rights(self.channel['channel_id'])
        await self.reply_success()
