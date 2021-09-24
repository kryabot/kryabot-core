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
        self.period = 3
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
            broadcaster_id = int(data['subscription']['condition']['broadcaster_user_id'])
            topic = EventSubType(data['subscription']['type'])

            profile = next(filter(lambda p: p.twitch_id == broadcaster_id, self.profiles), None)
            if not profile:
                self.logger.info('Received event for Twitch ID {} but profile not found'.format(broadcaster_id))

            if topic.eq(EventSubType.STREAM_ONLINE) or topic.eq(EventSubType.STREAM_OFFLINE):
                # START Or FINISH
                event = TwitchEvent(profile, data)
                await event.profile.store_to_cache(self.manager.db.redis)
                stream_data = await self.manager.api.twitch.get_stream_info_by_ids([profile.twitch_id])
                event.parse_stream_data(stream_data['data'][0] if stream_data and stream_data['data'] else None)
            else:
                # UPDATE
                event = profile.last_event
                # TODO: build event again if none and stream is online (api call)
                if not event or event.is_down():
                    # update when stream is off or we dont have start event (for example after restart)
                    self.logger.info('Skipping update for {}'.format(profile.twitch_name))
                    continue
                event.parse_update(data['event'])

                if event.update and not event.updated_data:
                    # Nothing changed
                    self.logger.info('[{}] Skipping update because nothing changed'.format(profile.twitch_id))
                    continue

            # Publish event to Info bot
            self.loop.create_task(self.manager.event(event))

            self.logger.info('Export data: {}'.format(event.export()))
            # Publish event to Twitch/Telegram bot
            await self.manager.db.redis.publish_event(redis_key.get_streams_forward_data(), event.export())

    async def subscribe_all(self)->None:
        current_on = await self.manager.api.twitch_events.get_all(topic=EventSubType.STREAM_ONLINE)
        current_off = await self.manager.api.twitch_events.get_all(topic=EventSubType.STREAM_OFFLINE)
        current_updates = await self.manager.api.twitch_events.get_all(topic=EventSubType.CHANNEL_UPDATE)

        for profile in self.profiles:
            exists_on = next(filter(lambda event: int(event['condition']['broadcaster_user_id']) == int(profile.twitch_id), current_on['data']), None)
            exists_off = next(filter(lambda event: int(event['condition']['broadcaster_user_id']) == int(profile.twitch_id), current_off['data']), None)
            exists_update = next(filter(lambda event: int(event['condition']['broadcaster_user_id']) == int(profile.twitch_id), current_updates['data']), None)
            await self.subscribe_profile(profile, stream_on=exists_on is None, stream_off=exists_off is None, stream_updates=exists_update is None)

    async def subscribe_profile(self, profile: TwitchProfile, stream_on: bool=True, stream_off: bool=True, stream_updates: bool=True)->None:
        topics = []

        if stream_on:
            topics.append(EventSubType.STREAM_ONLINE)

        if stream_off:
            topics.append(EventSubType.STREAM_OFFLINE)

        if stream_updates:
            topics.append(EventSubType.CHANNEL_UPDATE)

        if not topics:
            return

        try:
            self.logger.info('Subscribing events for profile {} {}'.format(profile.twitch_id, profile.twitch_name))
            response, errors = await self.manager.api.twitch_events.create_many(profile.twitch_id, topics=topics)
            if errors:
                for error in errors:
                    self.logger.exception(error)
        except Exception as ex:
            self.logger.exception(ex)

    async def update_data(self, start: bool = False):
        self.logger.info('Updating twitch listener data')

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
