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
