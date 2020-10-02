import logging
from datetime import datetime, timedelta
from typing import Dict
from random import randint

from object.Base import Base

logger = logging.getLogger('krya.tg')


class HalloweenChannels(Base):
    def __init__(self):
        self.channels: Dict = {}

    def new_channel(self, channel_id):
        self.channels[channel_id] = HalloweenChannel(channel_id)

    def new_spawn(self, channel_id, message_id):
        self.channels[channel_id].save(message_id)

    def is_active(self, channel_id, message_id)->bool:
        return self.channels[channel_id].is_active(message_id)

    def set_used(self, channel_id, message_id):
        self.channels[channel_id].set_used(message_id)


class HalloweenChannel(Base):
    def __init__(self, channel_id):
        self.channel_id: int = channel_id
        self.pumpkins: Dict(int, Pumpkin) = {}
        self.last_spawn: datetime = datetime.utcnow()

    def is_active(self, msg_id: int)->bool:
        if not int(msg_id) in self.pumpkins:
            return False

        return self.pumpkins[int(msg_id)].active

    def set_used(self, msg_id)->None:
        if not int(msg_id) in self.pumpkins:
            return

        self.pumpkins[int(msg_id)] = None

    def can_spawn(self)->bool:
        delay = randint(10, 120)

        if self.last_spawn + timedelta(minutes=delay) < datetime.utcnow():
            self.last_spawn = datetime.utcnow()
            return True

        return False

    def save(self, msg_id: int):
        self.pumpkins[int(msg_id)] = Pumpkin(msg_id)


class Pumpkin(Base):
    def __init__(self, msg_id):
        self.msg_id = msg_id
        self.active = True
