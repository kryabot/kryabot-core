from tgbot.events.global_events.GlobalEventProcessor import GlobalEventProcessor
from tgbot.events.global_events.easter import process_easter


class EasterEventProcessor(GlobalEventProcessor):
    def __init__(self):
        super().__init__()
        self.event_name = "easter"
        self.get_logger().info("Created EasterEventProcessor")
        self.register_task(self.easter)

    async def easter(self, client):
        self.get_logger().info("Started easter")

    async def process(self, global_event, event, channel):
        await process_easter(global_event, event, channel)
