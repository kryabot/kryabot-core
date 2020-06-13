from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand


class DeleteAward(BaseCommand):
    command_names = ['deleteaward']
    access_level = UserAccess.CHAT_ADMIN

    def __init__(self, event, parsed):
        super().__init__(event, parsed, DeleteAward.access_level)

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return

        try:
            keyword = self.parsed.pop(1)
        except:
            await self.reply_fail(self.get_translation('KB_NO_KEYWORD'))
            return

        existing_awards = await self.db.getChannelTgAwards(self.channel['channel_id'], self.channel['user_id'])
        award = [awd for awd in existing_awards if awd['award_key'].lower() == keyword.lower()]

        if existing_awards is None or len(award) == 0:
            await self.reply_fail(self.get_translation('CMD_AWARD_NOT_FOUND').format(oldkey=keyword))
        else:
            await self.db.deleteTgAward(self.channel['user_id'], award[0]['tg_award_id'], self.sender['user_id'])
            await self.reply_success(self.get_translation('CMD_AWARD_DELETE').format(award_keyword=keyword))
