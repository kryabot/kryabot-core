from infobot.Listener import Listener


class GoodgameListener(Listener):
    def __init__(self, manager):
        super().__init__(manager)

    @Listener.repeatable
    async def listen(self):
        self.logger.debug('Checking goodgame data')