from infobot.Listener import Listener


class WasdListener(Listener):
    def __init__(self, manager):
        super().__init__(manager)
        self.period = 300
        # self.profiles: List[BoostyProfile] = []
        # self.update_type = BoostyUpdate

    @Listener.repeatable
    async def listen(self):
        self.logger.debug('Checking wasd data')

    # def get_new_profile_instance(self, *args, **kwargs):
    #     return BoostyProfile(*args, **kwargs)