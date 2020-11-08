from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand
from tgbot.events.global_events.HalloweenEventProcessor import HalloweenEventProcessor
from utils.date_diff import get_datetime_diff_text
from datetime import datetime, timedelta


class SpawnLove(BaseCommand):
    command_names = ['spawnlove']
    access_level = UserAccess.SUPER_ADMIN

    def __init__(self, event, parsed):
        super().__init__(event, parsed, SpawnLove.access_level)

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return

        processor = HalloweenEventProcessor.get_instance()
        processor.channels.new_channel(self.channel['tg_chat_id'], self.channel['bot_lang'])
        await processor.channels.channels[self.channel['tg_chat_id']].spawn_love_pumpkin(self.client, 25, test=True)
