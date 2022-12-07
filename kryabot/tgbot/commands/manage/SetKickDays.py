from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand


class SetKickDays(BaseCommand):
    command_names = ['setkickdays']
    access_level = UserAccess.CHAT_SUDO

    def __init__(self, event, parsed):
        super().__init__(event, parsed, SetKickDays.access_level)

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return

        if self.channel['kick_mode'] != 'PERIOD':
            await self.reply_fail(self.get_translation('CMD_MK_PERIOD_WRONG_KICK_MODE'))
            return

        try:
            new_period = int(self.parsed.pop(1))
        except:
            await self.reply_incorrect_input()
            return

        if new_period is None or new_period < 0:
            new_period = 0

        if new_period > 14:
            await self.reply_fail(self.get_translation('CMD_MK_PERIOD_BAD_RANGE').format(np=new_period))
            return

        if new_period == self.channel['auto_mass_kick']:
            await self.reply_fail(self.get_translation('CMD_MK_PERIOD_EXISTS').format(np=new_period))
            return

        await self.db.setSubchatKickPeriod(self.channel['tg_chat_id'], new_period)

        if new_period == 0:
            await self.reply_success(self.get_translation('CMD_MK_PERIOD_DISABLED').format(np=new_period))
        else:
            await self.reply_success(self.get_translation('CMD_MK_PERIOD_CHANGED').format(np=new_period))


