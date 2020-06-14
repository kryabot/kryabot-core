from typing import List
from datetime import datetime, timedelta
from infobot.LinkTable import LinkTable
from infobot.Profile import Profile


class TwitchProfile(Profile):
    def __init__(self, raw, ts):
        self.twitch_name: str = None
        self.twitch_id: int = None
        self.user_id: int = None
        self.stream_history: List = []
        self.last_stream_start = None
        self.last_event = None
        self.last_webhook_subscribe: datetime = None

        super().__init__(raw, ts, LinkTable.TWITCH)

    def update(self, raw, ts):
        super().update(raw, ts)
        self.twitch_name = str(raw['name'])
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