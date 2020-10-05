from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand
from tgbot.events.global_events.HalloweenEventProcessor import HalloweenEventProcessor
from utils.date_diff import get_datetime_diff_text
from datetime import datetime, timedelta


class SpawnBoss(BaseCommand):
    command_names = ['spawnboss']
    access_level = UserAccess.SUPER_ADMIN

    def __init__(self, event, parsed):
        super().__init__(event, parsed, SpawnBoss.access_level)

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return

        processor = HalloweenEventProcessor.get_instance()
        await processor.channels.channels[self.channel['tg_chat_id']].spawn_boss(self.client, 25)
