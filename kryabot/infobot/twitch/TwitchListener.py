from typing import List
from dateutil.parser import parse

from api.twitchevents.twitch_events import EventSubType
from infobot.UpdateBuilder import TwitchUpdate, UpdateAction
from infobot.Listener import Listener
from infobot.twitch.TwitchEvents import TwitchEvent
from infobot.twitch.TwitchProfile import TwitchProfile
import utils.redis_key as redis_key
from utils.array import split_array_into_parts


class TwitchListener(Listener):
    def __init__(self, manager):
        super().__init__(manager)
        self.period = 3
        self.profiles: List[TwitchProfile] = []
        self.last_subscribe = None
        self.update_type = TwitchUpdate
        self.unsubscribes: List[int] = []

    async def start(self):
        await super().start()
        await self.recover_status()
        await self.subscribe_all()
        self.period = 3

    @Listener.repeatable
    async def listen(self):
        while True:
            self.loop.create_task(self.unsubscribe_all())
            data = await self.manager.db.redis.get_one_from_list_parsed(redis_key.get_streams_data())
            if data is None:
                break

            self.logger.info(data)
            broadcaster_id = int(data['subscription']['condition']['broadcaster_user_id'])
            topic = EventSubType(data['subscription']['type'])

            profile = next(filter(lambda p: p.twitch_id == broadcaster_id, self.profiles), None)
            if not profile:
                self.unsubscribes.append(broadcaster_id)
                self.logger.info('Received event for Twitch ID {} but profile not found'.format(broadcaster_id))
                continue

            event = None

            if topic.eq(EventSubType.STREAM_ONLINE):
                is_live = data['event']['type'] == 'live'
                if is_live and profile.last_event and profile.last_event.is_recovery():
                    event = profile.last_event
                    event.set_recovery()
                else:
                    event = TwitchEvent(profile, data)

                await event.profile.store_to_cache(self.manager.db.redis)
                stream_data = await self.manager.api.twitch.get_stream_info_by_ids([profile.twitch_id])
                event.parse_stream_data(stream_data['data'][0] if stream_data and stream_data['data'] else None)
            elif topic.eq(EventSubType.STREAM_OFFLINE):
                event = profile.last_event
                if not event or event.finish:
                    # update when stream is off or we dont have start event (for example after restart)
                    self.logger.info('Skipping finish for {}'.format(profile.twitch_name))
                    continue

                event.parse_finish(data['event'])
            elif topic.eq(EventSubType.CHANNEL_UPDATE):
                event = profile.last_event
                # TODO: build event again if none and stream is online (api call)
                if not event or event.finish:
                    # update when stream is off or we dont have start event (for example after restart)
                    self.logger.info('Skipping update for {}'.format(profile.twitch_name))
                    continue
                event.parse_update(data['event'])

                if event.update and not event.updated_data:
                    # Nothing changed
                    self.logger.info('[{}] Skipping update because nothing changed'.format(profile.twitch_id))
                    continue

            if not event:
                continue

            # Publish event to Info bot
            self.loop.create_task(self.manager.event(event))

            self.logger.info('Export data: {}'.format(event.export()))
            # Publish event to Twitch/Telegram bot
            await self.manager.db.redis.publish_event(redis_key.get_streams_forward_data(), event.export())

    async def subscribe_all(self) -> None:
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

    async def recover_status(self):
        full_ids = list(map(lambda p: p.twitch_id, self.profiles))
        ids_parts = split_array_into_parts(full_ids, 50)
        stream_datas = []
        for ids in ids_parts:
            data = await self.manager.api.twitch.get_stream_info_by_ids(ids)
            for info in data['data']:
                stream_datas.append(info)

        for profile in self.profiles:
            stream_info = next(filter(lambda row: int(row['user_id']) == int(profile.twitch_id), stream_datas), None)
            if stream_info is None:
                continue

            if isinstance(stream_info['started_at'], str):
                stream_info['started_at'] = parse(stream_info['started_at'])

            # Create event, add data and mark it as start
            event = TwitchEvent(profile, {'event': stream_info})
            event.parse_stream_data(stream_info)
            event.set_start()

    async def on_update(self, data: TwitchUpdate):
        self.logger.info('TwitchListener update: {}'.format(data.to_json()))
        if data.action == UpdateAction.UPDATE:
            await self.update_data()
        elif data.action == UpdateAction.REMOVE:
            profile = next(filter(lambda p: p.user_id == data.user_id, self.profiles), None)
            if profile and self.has_link(profile):
                self.logger.info('Skipping remove of profile {} because link exist'.format(profile.twitch_name))
                return

            self.logger.info('Removing profile {}'.format(profile.twitch_name))
            self.unsubscribes.append(profile.twitch_id)
            await self.remove_profile(profile)
        else:
            self.logger.error('Unhandled update action: {}'.format(data.action))

    async def unsubscribe_all(self):
        if not self.unsubscribes:
            return

        current_on = await self.manager.api.twitch_events.get_all(topic=EventSubType.STREAM_ONLINE)
        current_off = await self.manager.api.twitch_events.get_all(topic=EventSubType.STREAM_OFFLINE)
        current_updates = await self.manager.api.twitch_events.get_all(topic=EventSubType.CHANNEL_UPDATE)

        all_subscribes = current_on['data'] + current_off['data'] + current_updates['data']
        for remove_twitch_id in self.unsubscribes:
            self.logger.info('Unsubscribing twitch ID {}'.format(remove_twitch_id))
            profile = next(filter(lambda p: p.twitch_id == remove_twitch_id, self.profiles), None)
            if profile:
                self.logger.info('Received removal of twitch ID {}, but profile {} {} still exists'.format(remove_twitch_id, profile.twitch_id, profile.twitch_name))
                continue

            existing_subscribes = filter(lambda event: int(event['condition']['broadcaster_user_id']) == int(remove_twitch_id), all_subscribes)
            for sub in existing_subscribes:
                await self.manager.api.twitch_events.delete(sub['id'])

        self.unsubscribes = []
