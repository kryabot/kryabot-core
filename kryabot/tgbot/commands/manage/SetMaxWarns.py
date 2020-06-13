from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand


class SetMaxWarns(BaseCommand):
    command_names = ['setmaxwarns']
    access_level = UserAccess.CHAT_SUDO

    def __init__(self, event, parsed):
        super().__init__(event, parsed, SetMaxWarns.access_level)

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return

        try:
            max_warns = int(self.parsed.pop(1))
        except:
            await self.reply_incorrect_input()
            return

        if max_warns is None or max_warns < 0:
            max_warns = 0

        if max_warns == self.channel['max_warns']:
            await self.reply_fail(self.get_translation('CMD_MAX_WARNS_EXISTS').format(mw=max_warns))
            return

        await self.db.updateSubchatMaxWarns(self.channel['tg_chat_id'], max_warns)
        await self.reply_success(self.get_translation('CMD_MAX_WARNS_CHANGED').format(mw=max_warns))


