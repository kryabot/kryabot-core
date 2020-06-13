from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand


class SetMinSubMonths(BaseCommand):
    command_names = ['setminsubmonths']
    access_level = UserAccess.CHAT_SUDO

    def __init__(self, event, parsed):
        super().__init__(event, parsed, SetMinSubMonths.access_level)
        self.command_name = 'setminsubmonths'

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return

        try:
            new_limit = int(self.parsed.pop(1))
        except:
            await self.reply_incorrect_input()
            return

        if new_limit is None or new_limit < 0:
            new_limit = 0

        if new_limit > 120:
            await self.reply_fail(self.get_translation('CMD_MIN_SUB_MONTH_TOO_BIG').format(np=new_limit))
            return

        if self.channel['join_sub_only'] == 0:
            await self.reply_fail(self.get_translation('CMD_MIN_SUB_MONTH_BAD_MODE'))
            return

        if new_limit == self.channel['min_sub_months']:
            await self.reply_fail(self.get_translation('CMD_MIN_SUB_MONTH_EXISTS').format(np=new_limit))
            return

        await self.db.setSubchatMinSubMonths(self.channel['tg_chat_id'], new_limit)

        if new_limit == 0:
            await self.reply_success(self.get_translation('CMD_MIN_SUB_MONTH_DISABLED').format(np=new_limit))
        else:
            await self.reply_success(self.get_translation('CMD_MIN_SUB_MONTH_CHANGED').format(np=new_limit))
