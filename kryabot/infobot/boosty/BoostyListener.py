import asyncio
from typing import List

from infobot.Listener import Listener
from infobot.boosty.BoostyEvents import BoostyEvent
from infobot.boosty.BoostyProfile import BoostyProfile


class BoostyListener(Listener):
    def __init__(self, manager):
        super().__init__(manager)
        self.period = 600
        self.profiles: List[BoostyProfile] = []

    @Listener.repeatable
    async def listen(self):
        self.logger.debug('Checking boosty data')

        for profile in self.profiles:
            await asyncio.sleep(5)

            repeat = True
            offset = None
            while repeat:
                if offset is not None:
                    await asyncio.sleep(5)
                data = await self.manager.api.boosty.get_user_posts(profile.boosty_username, limit=5, offset=offset)
                if data is None or 'data' not in data:
                    break

                if 'extra' not in data and 'offset' not in data['extra']:
                    break

                offset = data['extra']['offset']

                for post in data['data']:
                    if profile.post_exists(str(post['id'])):
                        repeat = False
                        break

                    event = BoostyEvent(profile, post)
                    self.loop.create_task(self.manager.event(event))

    async def update_data(self, start: bool = False)->None:
        self.logger.info('Updating boosty listener data')

        try:
            profiles = await self.db.getBoostyProfiles()
            history = await self.db.getBoostyHistory()

            await self.update_profiles(profiles, history)
        except Exception as ex:
            self.logger.exception(ex)

    def get_new_profile_instance(self, *args, **kwargs):
        return BoostyProfile(*args, **kwargs)
