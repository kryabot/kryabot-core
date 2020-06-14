import asyncio
from typing import List

from api.twitch import Twitch
from infobot.Listener import Listener
from infobot.twitch.TwitchEvents import TwitchEvent
from infobot.twitch.TwitchProfile import TwitchProfile
import utils.redis_key as redis_key


class TwitchListener(Listener):
    def __init__(self, manager):
        super().__init__(manager)
        self.period = 500000
        self.profiles: List[TwitchProfile] = []
        self.api: Twitch = Twitch(redis=manager.db.redis, cfg=manager.cfg)
        self.last_subscribe = None

    async def start(self):
        await super().start()
        self.period = 3

    @Listener.repeatable
    async def listen(self):
        await self.subscribe_all()

        while True:
            data = await self.manager.db.redis.get_one_from_list_parsed(redis_key.get_streams_data())
            if data is None:
                break

            self.logger.info(data)

            for prof in self.profiles:
                if prof.twitch_id == data['twitch_id']:
                    event = TwitchEvent(prof, data['data'])
                    await event.translate(self.api)

                    # Publish event to Info bot
                    self.loop.create_task(self.manager.event(event))

                    # Publish event to Twitch/Telegram bot
                    await self.manager.db.redis.publish_event(redis_key.get_streams_forward_data(), event.export())

    async def subscribe_all(self)->None:
        for profile in self.profiles:
            if profile.need_resubscribe():
                await self.subscribe_profile(profile)
                profile.subscribed()
                await asyncio.sleep(2)

    async def subscribe_profile(self, profile: TwitchProfile)->None:
        self.logger.info('Refreshing stream webhook for {}'.format(profile.twitch_name))
        await self.api.webhook_subscribe_stream(profile.twitch_id, profile.twitch_name)

    async def update_data(self, start: bool = False):
        try:
            profiles = await self.db.getTwitchProfiles()
            history = await self.db.getTwitchHistory()

            await self.update_profiles(profiles, history, start)
        except Exception as ex:
            self.logger.exception(ex)

    def get_new_profile_instance(self, *args, **kwargs)->TwitchProfile:
        return TwitchProfile(*args, **kwargs)

    async def handle_new_profile(self, profile: TwitchProfile):
        await self.subscribe_profile(profile)
