from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand


class SetReminderCooldown(BaseCommand):
    command_names = ['setremindercd']
    access_level = UserAccess.CHAT_SUDO

    def __init__(self, event, parsed):
        super().__init__(event, parsed, SetReminderCooldown.access_level)

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return

        try:
            new_cd = int(self.parsed.pop(1))
        except:
            await self.event.reply(self.get_translation('CMD_REMINDER_CD_NOT_NUMBER'))
            return

        if new_cd is None or new_cd < 0:
            new_cd = 0

        if new_cd == self.channel['reminder_cooldown']:
            await self.event.reply(self.get_translation('CMD_REMINDER_CD_NO_CHANGE'))
            return

        await self.db.saveReminderCooldown(self.channel['channel_subchat_id'], new_cd)

        reply_text = ''
        if new_cd == 0:
            reply_text = self.get_translation('CMD_REMINDER_CD_DISABLED')

        if self.channel['reminder_cooldown'] == 0 and new_cd > 0:
            reply_text = self.get_translation('CMD_REMINDER_CD_ENABLED').format(reminderhours=str(new_cd))

        if reply_text == '':
            reply_text = self.get_translation('CMD_REMINDER_CD_UPDATED').format(cd_old=self.channel['reminder_cooldown'], cd_new=new_cd)

        await self.client.init_channels()
        await self.event.reply(reply_text)