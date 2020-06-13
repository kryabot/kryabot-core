from infobot.Listener import Listener


class YoutubeListener(Listener):
    def __init__(self, manager):
        super().__init__(manager)

    @Listener.repeatable
    async def listen(self):
        self.logger.debug('Checking youtube data')