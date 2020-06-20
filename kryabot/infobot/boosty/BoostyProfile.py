from typing import List

from infobot.LinkTable import LinkTable
from infobot.Profile import Profile


class BoostyProfile(Profile):
    def __init__(self, raw, ts):
        self.boosty_username: str = None
        self.last_post_id: str = None

        self.post_history: List = []

        super().__init__(raw, ts, LinkTable.BOOSTY)

    def post_exists(self, post_media_id: str)->bool:
        return self.last_post_id == post_media_id or self.in_list(self.post_history, 'post_id', post_media_id)

    def update(self, raw, ts):
        super().update(raw, ts)
        self.boosty_username = str(raw['username'])

    def add_post_history(self, mediaid, date):
        self.last_post_id = mediaid
        self.post_history.append({"post_id": mediaid, 'created_ts': date})

    def set_history(self, full_history):
        self.post_history = [row for row in full_history if row[self.profile_id_key] == self.profile_id]

    def is_first_bot_post(self):
        return len(self.post_history) <= 1
