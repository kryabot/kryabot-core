from datetime import datetime
from enum import Enum
from random import randint
from typing import Dict

from object.Base import Base


class ItemType(Enum):
    ITEM_SNOWING = 1


class WinterItem(Base):
    def __init__(self, msg_id: int, hp: int=1, test: bool=False):
        self.type: ItemType = None
        self.msg_id: int = msg_id
        self.max_hp: int = hp
        self.current_hp: int = hp
        self.active: bool = True
        self.test: bool = test
        self.last_activity: datetime = datetime.utcnow()
        self.created: datetime = datetime.utcnow()
        self.participants: Dict[int, int] = {}
        self.can_die: bool = False

    def calc_damage(self)->int:
        return 1

    def is_active(self):
        return self.active

    def already_interacted(self, user_id: int)->bool:
        return user_id in self.participants

    def interact(self, user_id: int)->bool:
        if not self.is_active():
            return False

        if self.can_die:
            dmg = self.calc_damage()
        else:
            dmg = 0

        self.current_hp -= dmg
        self.current_hp = max(self.current_hp, 0)

        self.last_activity: datetime = datetime.utcnow()

        if user_id in self.participants:
            self.participants[user_id] += dmg
        else:
            self.participants[user_id] = dmg

        # Last hit
        if self.current_hp <= 0:
            self.active = False
            return True

        return False


class Snowing(WinterItem):
    def __init__(self, msg_id: int, hp: int=1, test: bool=False):
        super().__init__(msg_id=msg_id, hp=hp, test=test)
        self.type = ItemType.ITEM_SNOWING
        self.can_die = False
