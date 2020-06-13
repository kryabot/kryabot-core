from datetime import datetime
from typing import List

from infobot.Event import Event
from infobot.instagram.InstagramProfile import InstagramProfile
from object.Base import Base


class InstagramStoryEvent(Event):
    def __init__(self, profile: InstagramProfile):
        super().__init__(profile)
        self.profile: InstagramProfile = profile
        self.unique_id: str = None
        self.latest_media_utc: datetime = None
        self.itemcount: int = 0
        self.owner: str = None
        self.items: List[InstagramStoryItem] = []

    def add_story(self, story):
        self.unique_id = story.unique_id
        self.latest_media_utc = story.latest_media_utc
        self.itemcount = story.itemcount
        self.owner = story.owner_username

        for item in story.get_items():
            if self.profile.story_exists(item.mediaid):
                continue

            self.items.append(InstagramStoryItem(item))
            self.profile.add_story_history(item.mediaid, item.date)

    def is_new(self):
        return len(self.items) > 0

    async def save(self, db):
        for item in self.items:
            await db.saveInstagramStoryEvent(self.profile.profile_id, item.media_id, item.date)


class InstagramStoryItem(Base):
    def __init__(self, item):
        self.media_id: str = str(item.mediaid)
        self.shortcode: str = item.shortcode
        self.owner: str = item.owner_username
        self.date: datetime = item.date_utc
        self.url: str = item.url
        self.typename: str = item.typename
        self.is_video: bool = item.is_video
        self.video_url: str = item.video_url
        self.external_url: str = None
        if 'story_cta_url' in item._node:
            self.external_url: str = item._node['story_cta_url']


class InstagramPostEvent(Event):
    def __init__(self, profile: InstagramProfile):
        super().__init__(profile)
        self.profile: InstagramProfile = profile
        self.is_instagram = True
        self.owner: str = None
        self.media_id: str = None
        self.url: str = None
        self.type: str = None
        self.text: str = None
        self.media_list: List[InstagramMedia] = []
        self.hashtags: List[str] = []
        self.mentions: List[str] = []
        self.is_video: bool = False
        self.video_url: str = None
        self.tagged_users: List[str] = []
        self.video_duration: float = 0
        self.is_sponsored: bool = False
        self.sponsored_users: List[str] = []
        self.shortcode: str = None

    def add_post(self, post):
        self.owner = post.owner_username
        self.date = post.date_utc
        self.media_id = str(post.mediaid)
        self.url = post.url
        self.type = post.typename
        self.text = post.caption
        self.hashtags = post.caption_hashtags
        self.mentions = post.caption_mentions
        self.is_video = post.is_video
        self.tagged_users = post.tagged_users
        self.video_url = post.video_url
        self.video_duration = post.video_duration
        self.shortcode = post.shortcode
        # self.is_sponsored = post.is_sponsored

        self.profile.add_post_history(self.media_id, self.date)
        for sidecar in post.get_sidecar_nodes():
            media = InstagramMedia()
            media.is_video = sidecar.is_video
            media.url = sidecar.display_url
            media.video_url = sidecar.video_url
            self.media_list.append(media)

        if not self.media_list:
            media = InstagramMedia()
            media.is_video = self.is_video
            media.url = self.url
            media.video_url = self.video_url
            self.media_list.append(media)

        # for user in post.sponsor_users():
        #     self.sponsored_users.append(user.username)

    def get_formatted_text(self):
        footer = '<a href="https://instagram.com/p/{}">Instagram</a>'.format(self.shortcode)

        return '{}\n\n{}'.format(self.text, footer)

    async def save(self, db):
        await db.saveInstagramPostEvent(self.profile.profile_id, self.media_id, self.date)


class InstagramMedia(Base):
    def __init__(self):
        self.is_video: bool = False
        self.url: str = None
        self.video_url: str = None