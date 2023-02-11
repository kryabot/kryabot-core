import json
from datetime import datetime, timedelta
from typing import List, Dict

from infobot.Event import Event
from infobot.boosty.BoostyProfile import BoostyProfile


class BoostyEvent(Event):
    def __init__(self, profile: BoostyProfile, data):
        super().__init__(profile)
        self.profile: BoostyProfile = profile
        self.created_at = None
        self.publish_time = None
        self.user_id: int = None
        self.id: str = None
        self.teasers: [] = None
        self.updated_at = None
        self.datas: List = []
        self.tags: List = []
        self.title: str = None
        self.access_name: str = None
        self.price: int = None
        self.public: bool = False

        if data:
            self.parse(data)

        self.teaser_text: str = self.parse_teaser_text()
        self.data_text: str = self.parse_data_text()

        self.videos: List[str] = []
        self.images: List[str] = []

        self.parse_media()
        if not self.images and not self.videos and not self.public:
            self.images.append('https://static.boosty.to/images/blur-cover.3INPE.jpg')

        self.profile.add_post_history(self.id, datetime.now())

    def parse(self, data):
        self.created_at = self.to_datetime(self.get_attr(data, 'createdAt', 0))
        self.publish_time = self.to_datetime(self.get_attr(data, 'publishTime', 0))
        self.user_id = self.get_attr(data['user'], 'id', None)
        self.id = self.get_attr(data, 'id', None)
        self.teasers = self.get_attr(data, 'teaser', [])
        self.updated_at = self.to_datetime(self.get_attr(data, 'updatedAt', 0))
        self.datas = self.get_attr(data, 'data', [])
        self.tags = self.get_attr(data, 'tags', [])
        self.title = str(self.get_attr(data, 'title', ''))
        access = self.get_attr(data, 'subscriptionLevel', {})
        self.access_name: str = str(self.get_attr(access, 'name', ''))
        self.price = int(self.get_attr(access, 'price', 0))
        self.public = bool(self.get_attr(data, 'hasAccess', False))

    def get_formatted_channel_url(self):
        return '<a href="{url}">{ch}</a>'.format(url=self.get_channel_url(), ch=self.profile.boosty_username)

    def get_channel_url(self):
        return 'https://boosty.to/{}'.format(self.profile.boosty_username)

    def get_post_url(self):
        return 'https://boosty.to/{}/posts/{}'.format(self.profile.boosty_username, self.id)

    def parse_teaser_text(self):
        text_result = ''

        for teaser in self.teasers:
            if teaser['type'] == 'text':
                if text_result != '':
                    text_result += '\n'
                text_result += self.get_attr(teaser, 'content', '')
            if teaser['type'] == 'link':
                if text_result != '':
                    text_result += '\n'
                text_result += self.get_parsed_link(teaser)

        if text_result == '':
            text_result = None
        return text_result

    def parse_data_text(self):
        text_result = ''

        for data in self.datas:
            if data['type'] == 'text':
                text_result += self.get_parsed_text(data)
            if data['type'] == 'link':
                text_result += self.get_parsed_link(data)

        if text_result == '':
            text_result = None
        return text_result

    def parse_media(self):
        for teaser in self.teasers:
            if teaser['type'] == 'video':
                self.videos.append(teaser['url'])
            if teaser['type'] == 'image':
                self.images.append(teaser['url'])

        for data in self.datas:
            if data['type'] == 'video':
                self.videos.append(data['url'])
            if data['type'] == 'image':
                self.images.append(data['url'])

    def get_parsed_text(self, data):
        if self.get_attr(data, 'modificator', '') == 'BLOCK_END':
            return '\n'

        data = json.loads(self.get_attr(data, 'content', []))

        return data[0] if data else ''

    def get_parsed_link(self, obj):
        return '<a hre="{}">{}</a>'.format(obj['url'], self.get_parsed_text(obj))

    def get_text(self):
        return self.teaser_text or self.data_text or ''

    async def save(self, db):
        try:
            await db.saveBoostEvent(self)
        except Exception as ex:
            self.profile.logger.error(ex)


class BoostyStreamEvent(Event):
    def __init__(self, profile: BoostyProfile):
        super().__init__(profile)
        self.profile: BoostyProfile = profile
        self.title: str = None
        self.start_time: datetime = None
        self.required_level: str = None
        self.likes: int = 0
        self.online: int = 0

        self.updated_data = {}
        self.profile.last_stream_event = self

        self.new_start: bool = False
        self.new_update: bool = False
        self.new_finish: bool = False

    def _extract_data(self, data):
        return (
            self.to_datetime(self.get_attr(data, 'createdAt', None)),
            self.get_attr(data, 'title', None),
            self.get_attr(self.get_attr(data, 'subscriptionLevel', None), 'name', None),
            self.get_attr(self.get_attr(data, 'count', None), 'likes', 0),
            self.get_attr(self.get_attr(data, 'count', None), 'viewers', 0),
        )

    def patch(self, new_data):
        self.updated_data = {}

        new_start_time = None
        new_title = None
        new_required_level = None
        new_likes = 0
        new_online = 0

        if new_data:
            new_start_time, new_title, new_required_level, new_likes, new_online = self._extract_data(new_data)
        print(self._extract_data(new_data))
        if self.title != new_title and new_title is not None:
            self.updated_data['title'] = new_title

        if self.required_level != new_required_level and new_required_level is not None:
            self.updated_data['required_level'] = new_required_level

        self.new_start = new_start_time is not None and self.start_time is None
        self.new_finish = new_start_time is None and self.start_time is not None
        self.new_update = not self.new_start and self.updated_data != {}

        self.start_time = new_start_time
        self.title = new_title
        self.required_level = new_required_level
        self.likes = new_likes
        self.online = new_online

    def requires_dispatch(self) -> bool:
        return self.new_start or self.new_update or self.new_finish

    def stream_started(self) -> bool:
        return self.new_start and not self.new_update

    def stream_updated(self) -> bool:
        return self.new_start and self.new_update

    def stream_finished(self) -> bool:
        return self.new_finish

    def get_stream_url(self) -> str:
        return "https://boosty.to/{}/streams/video_stream".format(self.profile.boosty_username)
