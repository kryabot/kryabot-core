from datetime import datetime, timedelta
from typing import List, Dict

from api.twitch_events import EventSubType
from infobot.Event import Event
from infobot.twitch.TwitchProfile import TwitchProfile


class TwitchEvent(Event):
    def __init__(self, profile: TwitchProfile, start_event):
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
        self.start_raw = start_event
        self.summary: [Dict] = []

        self.start: bool = False
        self.update: bool = False
        self.recovery: bool = False
        self.finish: bool = False

        if start_event:
            self.parse_start(start_event['event'])

        self.updated_data = []
        self.profile.last_event = self

    def parse_start(self, data):
        self.started_at = self.get_attr(data, 'started_at')
        self.type = str(self.get_attr(data, 'type', ''))
        self.twitch_event_id = str(self.get_attr(data, 'id'))
        self.profile.last_stream_start: datetime = self.started_at

    def parse_finish(self, data):
        self.set_finish()
        self.profile.last_stream_finish: datetime = datetime.utcnow()
        self.add_summary_finish()

    def parse_stream_data(self, data):
        self.set_start()

        title = self.get_attr(data, 'title')
        language = self.get_attr(data, 'language')
        game_id = self.get_attr(data, 'game_id')
        game_name = self.get_attr(data, 'game_name')

        self.title = title
        self.language = language
        self.game_id = game_id
        self.game_name = game_name

        self.add_summary_start()

    def parse_update(self, data):
        self.set_update()

        title = self.get_attr(data, 'title')
        language = self.get_attr(data, 'language')
        game_id = self.get_attr(data, 'category_id')
        game_name = self.get_attr(data, 'category_name')

        if self.title and self.title != title:
            self.updated_data.append({'title': title})
        if self.language and self.language != language:
            self.updated_data.append({'language': language})
        if self.game_id and self.game_id != game_id:
            self.updated_data.append({'game': game_id})
        if self.game_name and self.game_name != game_name:
            self.updated_data.append({'game_name': game_name})
            self.add_summary_category(game_name)

        self.title = title
        self.language = language
        self.game_id = game_id
        self.game_name = game_name

    def is_recovery(self)->bool:
        if self.profile.last_stream_finish is None:
            return False

        self.profile.logger.info('Checking of recovery for stream of {}, last stream = {}, utcnow = {}'.format(self.profile.twitch_name, self.profile.last_stream_finish.replace(tzinfo=None), datetime.utcnow()))
        if self.finish and self.profile.last_stream_finish.replace(tzinfo=None) + timedelta(seconds=300) > datetime.utcnow():
            self.set_recovery()
            return True

        return False

    def get_formatted_image_url(self):
        if self.finish:
            return None

        custom_url = 'https://static-cdn.jtvnw.net/previews-ttv/live_user_{}-1920x1080.jpg'.format(self.start_raw['event']['broadcaster_user_login'])
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
                "recovery": self.recovery,
                "start": self.start,
                "update": self.update,
                "down": self.finish,
                "game_id": self.game_id,
                "game_name": self.game_name,
                "img_url": self.get_formatted_image_url(),
                "type": self.type,
                "event_id": self.twitch_event_id,
                "online": self.online,
                "updated_data": self.updated_data,
                "summary": self.summary}

    def add_summary_start(self):
        if self.summary:
            self.summary.append({'type': 'resume', 'ts': datetime.utcnow()})
        else:
            self.summary.append({'type': 'start', 'ts': self.started_at})
            self.add_summary_category(self.game_name, self.started_at)

    def add_summary_category(self, category_name, when=None):
        self.summary.append({'type': 'game', 'ts': when if when else datetime.utcnow(), 'new_value': category_name})

    def add_summary_finish(self):
        self.summary.append({'type': 'finish', 'ts': datetime.utcnow()})

    def set_start(self):
        self.start = True
        self.update = False
        self.finish = False
        self.updated_data = []
        self.recovery = self.is_recovery()

    def set_update(self):
        self.start = False
        self.update = True
        self.finish = False
        self.updated_data = []
        self.recovery = False

    def set_finish(self):
        self.start = False
        self.update = False
        self.finish = True
        self.updated_data = []
        self.recovery = False

    def set_recovery(self):
        self.start = False
        self.update = False
        self.finish = False
        self.updated_data = []
        self.recovery = True
