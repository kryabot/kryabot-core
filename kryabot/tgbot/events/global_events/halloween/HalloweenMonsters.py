from datetime import datetime
from enum import Enum
from random import randint
from typing import Dict

from object.Base import Base


class MonsterType(Enum):
    ITEM_PUMPKIN_REGULAR = 1
    ITEM_PUMPKIN_BOSS = 2
    ITEM_PUMPKIN_BOX = 3


class Monster(Base):
    def __init__(self, msg_id: int, hp: int=1, test: bool=False):
        self.type: MonsterType = None
        self.msg_id: int = msg_id
        self.max_hp: int = hp
        self.current_hp: int = hp
        self.active: bool = True
        self.test: bool = test
        self.last_activity: datetime = datetime.utcnow()
        self.created: datetime = datetime.utcnow()
        self.damagers: Dict[int, int] = {}
        self.immortal: bool = False

    def is_active(self):
        return self.active

    def hit(self, user_id: int, dmg: int)->bool:
        if not self.is_active():
            return False

        self.current_hp -= dmg
        self.current_hp = max(self.current_hp, 0)
        self.last_activity: datetime = datetime.utcnow()

        if user_id in self.damagers:
            self.damagers[user_id] += dmg
        else:
            self.damagers[user_id] = dmg

        # Last hit
        if not self.immortal and self.current_hp <= 0:
            self.active = False
            return True

        return False

    def is_boss(self)->bool:
        return self.type == MonsterType.ITEM_PUMPKIN_BOSS

    def is_regular(self)->bool:
        return self.type == MonsterType.ITEM_PUMPKIN_REGULAR

    def is_box(self)->bool:
        return self.type == MonsterType.ITEM_PUMPKIN_BOX

    def kill(self):
        self.last_activity = datetime.utcnow()
        self.current_hp = 0
        self.active = False


class RegularPumpkin(Monster):
    def __init__(self, msg_id: int, hp: int=1, test: bool=False):
        super().__init__(msg_id=msg_id, hp=hp, test=test)
        self.type = MonsterType.ITEM_PUMPKIN_REGULAR


class BossPumpkin(Monster):
    def __init__(self, msg_id: int, hp: int, test: bool=False):
        super().__init__(msg_id=msg_id, hp=hp, test=test)
        self.type = MonsterType.ITEM_PUMPKIN_BOSS


class ChestBox(Monster):
    def __init__(self, msg_id: int, hp: int=1, test: bool=False):
        super().__init__(msg_id=msg_id, hp=hp, test=test)
        self.type = MonsterType.ITEM_PUMPKIN_BOX

    def hit(self, user_id: int, dmg: int):
        chance = randint(1, 100)

        self.max_hp += 1
        if chance > 20:
            return False

        return super().hit(user_id=user_id, dmg=dmg)


class LovePumpkin(Monster):
    def __init__(self, msg_id: int, hp: int, test: bool=False):
        super().__init__(msg_id=msg_id, hp=hp, test=test)
        self.type = MonsterType.ITEM_PUMPKIN_REGULAR
        self.immortal = True

    def hit(self, user_id: int, dmg: int):
        return super().hit(user_id=user_id, dmg=0)


class NumberPumpkin(Monster):
    def __init__(self, msg_id: int, hp: int, test: bool=False):
        super().__init__(msg_id=msg_id, hp=hp, test=test)
        self.type = MonsterType.ITEM_PUMPKIN_REGULAR
        self.immortal = True

    def hit(self, user_id: int, dmg: int):
        # Reset previous guess
        if user_id in self.damagers:
            self.damagers[user_id] = 0

        return super().hit(user_id=user_id, dmg=dmg)


class SilentPumpkin(Monster):
    def __init__(self, msg_id: int, hp: int, test: bool=False):
        super().__init__(msg_id=msg_id, hp=hp, test=test)
        self.type = MonsterType.ITEM_PUMPKIN_REGULAR
        self.immortal = True
