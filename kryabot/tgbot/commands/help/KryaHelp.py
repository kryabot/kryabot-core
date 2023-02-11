from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand


class KryaHelp(BaseCommand):
    command_names = ['kryahelp']
    access_level = UserAccess.VERIFIED

    def __init__(self, event, parsed):
        super().__init__(event, parsed, KryaHelp.access_level)

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return

        nl = '\n'
        label_yes = self.get_translation('GENERAL_YES').lower()
        label_no = self.get_translation('GENERAL_NO').lower()
        label_dis = self.get_translation('GENERAL_DISABLED').lower()

        reply = self.get_translation('HELP_MAIN_ANY')
        reply += nl + self.get_translation('HELP_MAIN_ADMIN')

        channel_mode = self.get_translation('MODE_ANY')
        if self.channel['join_sub_only']:
            channel_mode = self.get_translation('MODE_SUB_ONLY')
        elif self.channel['join_follower_only']:
            channel_mode = self.get_translation('MODE_FOLLOWER_ONLY')

        reply += nl + nl + self.get_translation('HELP_SETTING_TITLE')
        reply += nl + self.get_translation('HELP_SETTING_NAME').format(val=self.channel['channel_name'])
        reply += nl + self.get_translation('HELP_SETTING_INVITATION').format(
            val=label_yes if self.channel['enabled_join'] else label_no)
        reply += nl + self.get_translation('HELP_SETTING_MODE').format(val=channel_mode)
        reply += nl + self.get_translation('HELP_SETTING_KICK_MODE').format(self.channel['kick_mode'])
        reply += nl + self.get_translation('HELP_SETTING_AUTOKICK').format(
            val=label_yes if self.channel['auto_kick'] else label_no)
        reply += nl + self.get_translation('HELP_SETTING_AUTOMASSKICK').format(
            val=self.channel['auto_mass_kick'] if self.channel['auto_kick'] else label_dis)
        reply += nl + self.get_translation('HELP_SETTING_GET_CD').format(
            val=self.channel['getter_cooldown'])
        reply += nl + self.get_translation('HELP_SETTING_BANTIME').format(val=self.channel['ban_time'])

        await self.event.reply(reply)
