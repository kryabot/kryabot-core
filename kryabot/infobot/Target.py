from object.Base import Base


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
        self.lang: str = str(self.get_raw('lang'))

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
