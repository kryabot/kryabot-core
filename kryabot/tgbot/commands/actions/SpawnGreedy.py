from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand
from tgbot.events.global_events.HalloweenEventProcessor import HalloweenEventProcessor


class SpawnGreedy(BaseCommand):
    command_names = ['spawngreedy']
    access_level = UserAccess.SUPER_ADMIN

    def __init__(self, event, parsed):
        super().__init__(event, parsed, SpawnGreedy.access_level)

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return

        processor = HalloweenEventProcessor.get_instance()
        processor.channels.create(self.channel['tg_chat_id'], self.channel['bot_lang'])
        await processor.channels.channels[self.channel['tg_chat_id']].spawn_greedy(self.client, 100, test=False)
