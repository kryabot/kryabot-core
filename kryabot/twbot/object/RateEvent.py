import time
import random
from random import randint


class RateEvent:
    def __init__(self, logger=None):
        self.active = True
        self.channel_name = None
        self.by = None
        self.users = {}
        self.started = time.time()
        self.runtime = None
        self.until = None
        self.last_reminder = None
        self.text = None
        self.logger = logger

    async def is_active(self)-> bool:
        if self.runtime > 0 and self.until <= time.time():
            return False

        return self.active

    async def check_and_add(self, name, value):
        try:
            val = int(value)
        except Exception as ex:
            return

        if val is None or val < 1 or val > 10:
            return

        self.logger.info('[RateEvent] Adding participant {} with value {}'.format(name, val))
        await self.add(name, val)

    async def add(self, name: str, value: int):
        self.users[name] = int(value)

    async def can_remind(self)-> bool:
        if time.time() > self.last_reminder + 30:
            self.last_reminder = time.time()
            return True

        return False

    def get_avg(self)->float:
        sum = 0
        total = 0
        for val in self.users.values():
            if val is None or val <= 0 or val > 10:
                continue

            sum = sum + val
            total = total + 1.

        if total == 0:
            return 0

        return sum/total
