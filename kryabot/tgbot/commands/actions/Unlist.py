from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand
from telethon.tl.types import PeerUser
from utils.value_check import avoid_none


class Unlist(BaseCommand):
    command_names = ['unlist']
    access_level = UserAccess.CHAT_ADMIN

    def __init__(self, event, parsed):
        super().__init__(event, parsed, Unlist.access_level)
        self.must_be_reply = True

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return

        target_user = await self.client.get_entity(PeerUser(self.reply_message.sender_id))
        admin_user = await self.client.get_entity(PeerUser(self.event.message.sender_id))

        await self.client.report_to_monitoring(
            '[{chn}]\n User {afn} {aln} {au} {aid} removed special rights from user {tfn} {tln} {tu} {tid}'.format(
                chn=self.channel['channel_name'],
                afn=await avoid_none(admin_user.first_name),
                aln=await avoid_none(admin_user.last_name),
                au=await avoid_none(admin_user.username),
                aid=await avoid_none(self.event.message.sender_id),
                tfn=await avoid_none(target_user.first_name),
                tln=await avoid_none(target_user.last_name),
                tu=await avoid_none(target_user.username),
                tid=await avoid_none(self.reply_message.sender_id)
            ))

        await self.db.removeTgSpecialRight(self.channel['user_id'], self.reply_message.sender_id)
        await self.client.init_special_rights(self.channel['channel_id'])
        await self.reply_success(self.get_translation('CMD_UNLIST_SUCCESS'))
