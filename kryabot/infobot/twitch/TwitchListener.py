from typing import List

from api.twitch_events import EventSubType
from infobot.UpdateBuilder import TwitchUpdate
from infobot.Listener import Listener
from infobot.twitch.TwitchEvents import TwitchEvent
from infobot.twitch.TwitchProfile import TwitchProfile
import utils.redis_key as redis_key


class TwitchListener(Listener):
    def __init__(self, manager):
        super().__init__(manager)
        self.period = 500000
        self.profiles: List[TwitchProfile] = []
        self.last_subscribe = None
        self.update_type = TwitchUpdate

    async def start(self):
        await super().start()
        await self.subscribe_all()
        self.period = 3

    @Listener.repeatable
    async def listen(self):
        while True:
            data = await self.manager.db.redis.get_one_from_list_parsed(redis_key.get_streams_data())
            if data is None:
                break

            self.logger.info(data)

            for prof in self.profiles:
                if prof.twitch_id == data['twitch_id']:
                    event = TwitchEvent(prof, data['data'])
                    await event.translate(self.manager.api.twitch)
                    await event.profile.store_to_cache(self.manager.db.redis)
                    # Publish event to Info bot
                    self.loop.create_task(self.manager.event(event))

                    self.logger.info('Export data: {}'.format(event.export()))
                    # Publish event to Twitch/Telegram bot
                    await self.manager.db.redis.publish_event(redis_key.get_streams_forward_data(), event.export())

    async def subscribe_all(self)->None:
        current_on = await self.manager.api.twitch_events.get_all(topic=EventSubType.STREAM_ONLINE)
        current_off = await self.manager.api.twitch_events.get_all(topic=EventSubType.STREAM_OFFLINE)

        for profile in self.profiles:
            exists_on = next(filter(lambda event: int(event['condition']['broadcaster_user_id']) == int(profile.twitch_id), current_on['data']), None)
            exists_off = next(filter(lambda event: int(event['condition']['broadcaster_user_id']) == int(profile.twitch_id), current_off['data']), None)
            await self.subscribe_profile(profile, stream_on=exists_on is None, stream_off=exists_off is None)

    async def subscribe_profile(self, profile: TwitchProfile, stream_on: bool=True, stream_off: bool=True)->None:
        if stream_on:
            try:
                response = await self.manager.api.twitch_events.create(profile.twitch_id,
                                                                       topic=EventSubType.STREAM_ONLINE)
            except Exception as ex:
                self.logger.exception(ex)

        if stream_off:
            try:
                response = await self.manager.api.twitch_events.create(profile.twitch_id,
                                                                       topic=EventSubType.STREAM_OFFLINE)
            except Exception as ex:
                self.logger.exception(ex)

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
