from datetime import datetime, timedelta
from typing import Dict
from random import randint


class HalloweenChannel:
    def __init__(self, channel_id):
        self.channel_id: int = channel_id
        self.pumpkins: Dict(int, Pumpkin) = []
        self.last_spawn: datetime = datetime.utcnow()

    def is_active(self, msg_id: int)->bool:
        print("Checking if active {}".format(msg_id))
        print(self.pumpkins)
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
        self.pumpkins.append(Pumpkin(msg_id))
        print("After save")
        print(self.pumpkins)


class Pumpkin:
    def __init__(self, msg_id):
        self.msg_id = msg_id
        self.active = True
