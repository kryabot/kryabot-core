from datetime import datetime, timedelta
from typing import List, Dict

from api.twitch_events import EventSubType
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
            self.parse(data['event'])

        self.updated_data = []
        self.profile.last_event = self
        if self.is_start():
            self.profile.last_stream_start: datetime = self.started_at
        if self.is_down():
            self.profile.last_stream_finish: datetime = datetime.utcnow()

    def parse(self, data):
        self.started_at = self.get_attr(data, 'started_at')
        self.type = str(self.get_attr(data, 'type', ''))
        self.twitch_event_id = str(self.get_attr(data, 'id'))

    def parse_stream_data(self, data):
        self.updated_data = []

        title = self.get_attr(data, 'title')
        language = self.get_attr(data, 'language')
        game_id = self.get_attr(data, 'game_id')
        game_name = self.get_attr(data, 'game_name')

        if self.title and self.title != title:
            self.updated_data.append({'title': title})
            self.title = title
        if self.language and self.language != language:
            self.updated_data.append({'language': language})
            self.language = language
        if self.game_id and self.game_id != game_id:
            self.updated_data.append({'game_id': game_id})
            self.game_id = game_id
        if self.game_name and self.game_name != game_name:
            self.updated_data.append({'game_name': game_name})
            self.game_name = game_name

    def is_start(self)->bool:
        return self.raw['subscription']['type'] == EventSubType.STREAM_ONLINE.key and not self.updated_data

    def is_update(self)->bool:
        return self.is_start() and self.updated_data

    def is_down(self)->bool:
        return self.raw['subscription']['type'] == EventSubType.STREAM_OFFLINE.key

    def is_recovery(self)->bool:
        if self.profile.last_stream_finish is None:
            return False

        self.profile.logger.info('Checking of recovery for stream of {}, last stream = {}, utcnow = {}'.format(self.profile.twitch_name, self.profile.last_stream_finish.replace(tzinfo=None), datetime.utcnow()))
        if self.is_start() and self.profile.last_stream_finish.replace(tzinfo=None) + timedelta(seconds=300) > datetime.utcnow():
            return True

        return False

    def get_formatted_image_url(self):
        if self.is_down():
            return None

        custom_url = 'https://static-cdn.jtvnw.net/previews-ttv/live_user_{}-1080x720.jpg'.format(self.raw['event']['broadcaster_user_login'])
        custom_url += '?id={tmp_id}{seed}'.format(tmp_id=self.twitch_event_id, seed=str(int(datetime.now().timestamp())))
        return custom_url

    def get_formatted_channel_url(self):
        return '<a href="https://twitch.tv/{ch}">{ch}</a>'.format(ch=self.profile.twitch_name)

    def get_channel_url(self):
        return 'https://twitch.tv/{}'.format(self.profile.twitch_name)

    def export(self)->Dict:
        return {"channel_id": self.profile.twitch_id,
                "channel_name": self.profile.twitch_name,
                "channel_url": self.get_channel_url(),
                "started_at": self.started_at,
                "title": self.title,
                "recovery": self.is_recovery(),
                "start": self.is_start(),
                "update": self.is_update(),
                "down": self.is_down(),
                "game_id": self.game_id,
                "game_name": self.game_name,
                "img_url": self.get_formatted_image_url(),
                "type": self.type,
                "event_id": self.twitch_event_id,
                "online": self.online,
                "updated_data": self.updated_data}

    @property
    def start(self)->bool:
        return self.is_start()

    @property
    def down(self)->bool:
        return self.is_down()

    @property
    def update(self)->bool:
        return self.is_update()

    @property
    def recovery(self)->bool:
        return self.is_recovery()