from typing import List

from infobot.LinkTable import LinkTable
from infobot.Profile import Profile


class InstagramProfile(Profile):
    def __init__(self, raw, ts):
        self.instagram_name: str = None
        self.instagram_id: int = None
        self.check_stories: bool = None
        self.check_posts: bool = None
        self.last_story_id = None
        self.last_post_id = None

        self.post_history: List = []
        self.story_history: List = []

        super().__init__(raw, ts, LinkTable.INSTAGRAM)

    def post_exists(self, post_media_id: str)->bool:
        return self.last_post_id == post_media_id or self.in_list(self.post_history, 'media_id', post_media_id)

    def story_exists(self, story_media_id: str)->bool:
        return self.in_list(self.story_history, 'media_id', story_media_id)

    def update(self, raw, ts):
        super().update(raw, ts)
        self.instagram_name = str(raw['instagram_name'])
        self.instagram_id = int(raw['instagram_id'])
        self.check_stories = bool(raw['stories'] or 0)
        self.check_posts = bool(raw['posts'] or 0)

    def add_story_history(self, mediaid, date):
        self.last_story_id = mediaid
        self.story_history.append({"media_id": mediaid, 'object_date': date})

    def add_post_history(self, mediaid, date):
        self.last_post_id = mediaid
        self.post_history.append({"media_id": mediaid, 'object_date': date})

    def set_history(self, full_history):
        self.post_history = [row for row in full_history if row[self.profile_id_key] == self.profile_id and row['data_type'] == 'POST']
        self.story_history = [row for row in full_history if row[self.profile_id_key] == self.profile_id and row['data_type'] == 'STORY']

    def is_first_bot_post(self):
        return len(self.post_history) <= 1
