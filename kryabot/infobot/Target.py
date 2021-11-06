from object.Base import Base
import enum
from typing import List


class InfobotLang(enum.Enum):
    EN = 'en'
    RU = 'ru'


class Target(Base):
    def __init__(self, raw):
        self.raw = raw
        self.id: int = int(self.get_raw('infobot_id'))
        self.user_id: int = int(self.get_raw('user_id'))
        self.target_type: str = str(self.get_raw('target_type'))
        self.target_name: str = str(self.get_raw('target_name'))
        self.target_id: int = int(self.get_raw('target_id'))
        self.join_data: str = str(self.get_raw('join_data'))
        self.status_message: str = str(self.get_raw('status_message'))
        self.enabled: bool = bool(self.get_raw('enabled'))
        self.auth_key: str = str(self.get_raw('auth_key'))
        self.lang: InfobotLang = InfobotLang((self.get_raw('lang')))
        self.selected_links: List[any] = []
        self.selected_id: int = 0


        # Instagram
        self.insta_stories: bool = True
        self.insta_posts: bool = True

        # Twitch
        self.twitch_start: bool = True
        self.twitch_update: bool = True
        self.twitch_end: bool = True

        # Goodgame
        self.goodgame_start: bool = True
        self.goodgame_update: bool = True
        self.goodgame_end: bool = True

        # wasd
        self.wasd_start: bool = True
        self.wasd_update: bool = True
        self.wasd_end: bool = True

        # Twitter
        self.twitter_post: bool = True

        # VK
        self.vk_post: bool = True

        # Youtube
        self.youtube_video: bool = True

    def is_target_telegram(self)->bool:
        return self.target_type == 'TG'

    def get_raw(self, key=None):
        if key:
            return self.get_attr(self.raw, key)
        return self.raw

    def get_lang(self):
        return self.lang.value

    def get_selected_link(self):
        if not self.selected_links:
            raise ValueError('Infobot({}) got no entries in selected links, but should exist atleast one entry! Maybe you forgot to add @required_infobot_link decorator?'.format(self.id))
        return next(filter(lambda link: self.selected_id == link.link_id, self.selected_links), None)
