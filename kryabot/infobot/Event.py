from datetime import datetime

from infobot.Profile import Profile
from object.Base import Base


class Event(Base):
    def __init__(self, profile: Profile):
        self.profile: Profile = profile
        self.date: datetime = None

    async def save(self, db):
        pass
