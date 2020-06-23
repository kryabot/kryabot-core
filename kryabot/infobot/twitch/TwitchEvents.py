from datetime import datetime, timedelta
from typing import List, Dict

from infobot.Event import Event
from infobot.twitch.TwitchProfile import TwitchProfile


class TwitchEvent(Event):
    def __init__(self, profile: TwitchProfile, data):
        super().__init__(profile)
        self.profile: TwitchProfile = profile
        self.title: str = None
        self.game_id: int = None
        self.game_name: str = None
        self.started_at: datetime = None
        self.online: int = None
        self.url: str = None
        self.language: str = None
        self.communities: List = None
        self.tags: List = []
        self.type: str = None
        self.twitch_event_id: str = None
        self.event_id = None
        self.raw = data

        if data:
            self.parse(data[0])

        self.updated_data = []
        self.start: bool = self.is_start() or False
        self.update: bool = self.is_update() or False
        self.down: bool = self.is_down() or False
        self.recovery: bool = self.is_recovery() or False
        self.profile.last_event = self
        self.profile.last_stream_start: datetime = self.started_at

    def parse(self, data):
        self.title = self.get_attr(data, 'title', '')
        self.game_id = int(self.get_attr(data, 'game_id', 0))
        self.started_at = self.get_attr(data, 'started_at')
        self.online = int(self.get_attr(data, 'viewer_count', 0))
        self.url = str(self.get_attr(data, 'thumbnail_url', ''))
        self.language = str(self.get_attr(data, 'language', ''))
        self.communities = self.get_attr(data, 'community_ids')
        self.type = str(self.get_attr(data, 'type'))
        self.twitch_event_id = str(self.get_attr(data, 'id'))
        self.tags = self.get_attr(data, 'tag_ids', [])

    def is_start(self)->bool:
        return self.started_at is not None

    def is_update(self)->bool:
        updated = self.started_at and self.profile.last_stream_start == self.started_at

        if updated and self.profile.last_event:
            self.updated_data = []

            if self.title != self.profile.last_event.title:
                self.updated_data.append({'title': self.title})

            if self.game_id != self.profile.last_event.game_id:
                self.updated_data.append({'game': self.game_id})

            if self.communities != self.profile.last_event.communities:
                self.updated_data.append({'communities': self.communities})

            if self.type != self.profile.last_event.type:
                self.updated_data.append({'type': self.type})

        return updated

    def is_down(self)->bool:
        return not self.raw

    def is_recovery(self)->bool:
        if self.profile.last_stream_start is None:
            return False

        self.profile.logger.info('Checking of recovery for stream of {}, last stream = {}, utcnow = {}'.format(self.profile.twitch_name, self.profile.last_stream_start.replace(tzinfo=None), datetime.utcnow()))
        if self.is_start() and self.profile.last_stream_start.replace(tzinfo=None) + timedelta(seconds=300) > datetime.utcnow():
            return True

        return False

    def get_formatted_image_url(self):
        if self.down:
            return None

        custom_url = self.url.format(width=1280, height=720)
        custom_url += '?id={tmp_id}{seed}'.format(tmp_id=self.twitch_event_id, seed=str(int(datetime.now().timestamp())))
        return custom_url

    def get_formatted_channel_url(self):
        return '<a href="https://twitch.tv/{ch}">{ch}</a>'.format(ch=self.profile.twitch_name)

    def get_channel_url(self):
        return 'https://twitch.tv/{}'.format(self.profile.twitch_name)

    async def translate(self, api)->None:
        resp = await api.get_game_info(self.game_id)
        if resp and 'data' in resp and len(resp['data']) > 0:
            self.game_name = resp['data'][0]['name']

    def export(self)->Dict:
        return {"channel_id": self.profile.twitch_id,
                "channel_name": self.profile.twitch_name,
                "channel_url": self.get_channel_url(),
                "started_at": self.started_at,
                "title": self.title,
                "recovery": self.recovery,
                "start": self.start and not self.update,
                "update": self.update,
                "down": self.down,
                "game_id": self.game_id,
                "game_name": self.game_name,
                "img_url": self.get_formatted_image_url(),
                "type": self.type,
                "event_id": self.twitch_event_id,
                "online": self.online,
                "updated_data": self.updated_data}
