from tgbot.events.global_events.GlobalEventProcessor import GlobalEventProcessor


class EasterEventProcessor(GlobalEventProcessor):
    def __init__(self):
        super().__init__()
        self.event_name = "easter"
        self.get_logger().info("Created WinterEventProcessor")
        self.register_task(self.easter)

    async def easter(self, client):
        self.get_logger().info("Started easter")
