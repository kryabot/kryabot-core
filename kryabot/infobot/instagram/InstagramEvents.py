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

    def add_story(self, story, new_items):
        self.unique_id = story['id']
        self.latest_media_utc = self.to_datetime(story['latest_reel_media'])
        self.itemcount = story['media_count']
        self.owner = story['user']['username']

        for new_item in new_items:
            item = InstagramStoryItem(new_item)
            self.items.append(item)
            self.profile.add_story_history(item.media_id, item.date)

    async def save(self, db):
        for item in self.items:
            try:
                await db.saveInstagramStoryEvent(self.profile.profile_id, item.media_id, item.date)
            except Exception as ex:
                self.profile.logger.error(ex)

    def get_link_to_profile(self):
        return '🖼 <a href="https://instagram.com/{}">Instagram</a>'.format(self.owner)

    def get_mention_link(self, username: str)->str:
        return '<a href="https://instagram.com/{}">#{}</a>'.format(username, username)


class InstagramStoryItem(Base):
    def __init__(self, item):
        self.media_id: str = self.get_attr(item, 'pk', '')
        self.shortcode: str = self.get_attr(item, 'code', '')
        self.owner: str = self.get_attr(item['user'], 'username', '')
        self.date: datetime = self.to_datetime(self.get_attr(item, 'taken_at', 0))
        self.media_type: int = self.get_attr(item, 'media_type', 0)
        self.video_url: str = item['video_versions'][0]['url'] if 'video_versions' in item and item['video_versions'] else None
        self.image_url: str = item['image_versions2']['candidates'][0]['url'] if 'image_versions2' in item and item['image_versions2']['candidates'] else None
        self.is_video: bool = self.video_url is not None
        self.mentions: List[str] = []
        self.external_urls: List[str] = []

        if 'story_cta' in item:
            for cta in item['story_cta']:
                if 'links' in cta:
                    for link in cta['links']:
                        if 'webUri' in link:
                            self.external_urls.append(link['webUri'])

        if 'reel_mentions' in item:
            for mention in item['reel_mentions']:
                if 'user' in mention and 'username' in mention['user']:
                    self.mentions.append(mention['user']['username'])


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
        try:
            await db.saveInstagramPostEvent(self.profile.profile_id, self.media_id, self.date)
        except Exception as ex:
            self.profile.logger.error(ex)


class InstagramMedia(Base):
    def __init__(self):
        self.is_video: bool = False
        self.url: str = None
        self.video_url: str = None