from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand


class SetWarnExpire(BaseCommand):
    command_names = ['setwarnexpire']
    access_level = UserAccess.CHAT_SUDO

    def __init__(self, event, parsed):
        super().__init__(event, parsed, SetWarnExpire.access_level)

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return

        try:
            expire_hours = int(self.parsed.pop(1))
        except:
            await self.reply_incorrect_input()
            return

        if expire_hours is None or expire_hours < 1:
            await self.reply_incorrect_input()
            return

        if expire_hours == self.channel['warn_expires_in']:
            await self.reply_fail(self.get_translation('CMD_WARN_EXPIRE_EXISTS').format(mh=expire_hours))
            return

        await self.db.updateSubchatWarnExpireHours(self.channel['tg_chat_id'], expire_hours)
        await self.reply_success(self.get_translation('CMD_WARN_EXPIRE_CHANGED').format(mh=expire_hours))


