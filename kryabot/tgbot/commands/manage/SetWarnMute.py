from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand


class SetWarnMute(BaseCommand):
    command_names = ['setwarnmutetime']
    access_level = UserAccess.CHAT_SUDO

    def __init__(self, event, parsed):
        super().__init__(event, parsed, SetWarnMute.access_level)

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return

        try:
            mute_hours = int(self.parsed.pop(1))
        except:
            await self.reply_incorrect_input()
            return

        if mute_hours is None or mute_hours < 1:
            await self.reply_incorrect_input()
            return

        if mute_hours == self.channel['warn_mute_h']:
            await self.reply_fail(self.get_translation('CMD_WARN_MUTE_EXISTS').format(mh=mute_hours))
            return

        await self.db.updateSubchatWarnMuteHours(self.channel['tg_chat_id'], mute_hours)
        await self.reply_success(self.get_translation('CMD_WARN_MUTE_CHANGED').format(mh=mute_hours))


