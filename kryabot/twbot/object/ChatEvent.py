import time
from random import randint

from object.Base import Base


class ChatEvent(Base):
    def __init__(self, logger=None):
        self.active = None
        self.channel_name = None
        self.keyword = None
        self.by = None
        self.users = []
        self.started = None
        self.runtime = None
        self.until = None
        self.type = None
        self.last_reminder = None
        self.text = None
        self.logger = logger

    async def is_active(self)-> bool:
        if self.runtime > 0 and self.until <= time.time():
            return False

        return self.active

    async def add(self, name):
        if name in self.users:
            return

        self.users.append(name)
        self.logger('Current list: {}'.format(self.users))

    async def can_remind(self)-> bool:
        if time.time() > self.last_reminder + 30:
            self.last_reminder = time.time()
            return True

        return False

    async def roll_user(self):
        self.active = False
        self.runtime = 0

        if len(self.users) == 0:
            return None

        if len(self.users) == 1:
            return self.users[0]

        winIndex = randint(0, len(self.users) - 1)
        winner = self.users[winIndex]
        del self.users[winIndex]
        return winner
