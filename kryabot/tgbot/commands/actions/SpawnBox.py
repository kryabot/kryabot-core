from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand
from tgbot.events.global_events.HalloweenEventProcessor import HalloweenEventProcessor


class SpawnBox(BaseCommand):
    command_names = ['spawnbox']
    access_level = UserAccess.SUPER_ADMIN

    def __init__(self, event, parsed):
        super().__init__(event, parsed, SpawnBox.access_level)

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return

        processor = HalloweenEventProcessor.get_instance()
        processor.channels.create(self.channel['tg_chat_id'], self.channel['bot_lang'])
        await processor.channels.channels[self.channel['tg_chat_id']].spawn_box(self.client, 25, test=True)
