from typing import List
from datetime import datetime, timedelta
from infobot.LinkTable import LinkTable
from infobot.Profile import Profile
import utils.redis_key as redis_key


class TwitchProfile(Profile):
    def __init__(self, raw, ts):
        self.twitch_name: str = None
        self.display_name: str = None
        self.twitch_id: int = None
        self.user_id: int = None
        self.stream_history: List = []
        self.last_stream_start = None
        self.last_stream_finish = None
        self.last_event = None
        self.last_webhook_subscribe: datetime = None

        super().__init__(raw, ts, LinkTable.TWITCH)

    def update(self, raw, ts):
        super().update(raw, ts)
        self.twitch_name = str(raw['name'])
        self.display_name = str(raw['dname'])
        self.twitch_id = int(raw['tw_id'])
        self.user_id = int(raw['user_id'])

    def add_history(self, row):
        self.stream_history.append(row)

    def set_history(self, full_history):
        self.stream_history = [row for row in full_history if row[self.profile_id_key] == self.profile_id]

    def need_resubscribe(self)->bool:
        if self.last_webhook_subscribe is None:
            return True
        return self.last_webhook_subscribe < datetime.now() - timedelta(days=7)

    def subscribed(self)->None:
        self.last_webhook_subscribe = datetime.now()

    async def restore_from_cache(self, redis):
        cached = await redis.get_parsed_value_by_key(redis_key.get_twitch_stream_cache(self.twitch_id))
        self.last_stream_start = self.get_attr(cached, 'last_start', None)
        self.last_stream_finish = self.get_attr(cached, 'last_finish', None)

    async def store_to_cache(self, redis):
        cached = {'last_start': self.last_stream_start, 'last_finish': self.last_stream_finish}
        await redis.set_parsed_value_by_key(redis_key.get_twitch_stream_cache(self.twitch_id), cached, redis_key.ttl_week)
