from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand


class DryMassKick(BaseCommand):
    command_names = ['drymasskick']
    access_level = UserAccess.SUPER_ADMIN

    def __init__(self, event, parsed):
        super().__init__(event, parsed, DryMassKick.access_level)

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return

        params = []
        params.append({'key': 'not_verified', 'enabled': 1})
        params.append({'key': 'not_sub', 'enabled': self.channel['join_sub_only']})
        params.append({'key': 'not_follower', 'enabled': self.channel['join_follower_only']})
        params.append({'key': 'not_active', 'enabled': 1})

        await self.client.run_channel_refresh_new(self.channel, kick=True, params=params, dry_run=True)
        await self.reply_success()
