from enum import Enum
from typing import List


class AccessType(Enum):
    BOT_ADMIN = 10
    BOT_MOD = 9
    CHANNEL_OWNER = 8
    CHANNEL_MOD = 7
    CHANNEL_VIP = 6
    CHANNEL_SUB = 5
    CHANNEL_FOLLOWER = 4
    CHANNEL_USER = 3
    CHANNEL_ANY = 2

    @staticmethod
    def admin_package() -> List:
        return [AccessType.BOT_ADMIN, AccessType.BOT_MOD] + AccessType.mod_package()

    @staticmethod
    def mod_package() -> List:
        return [AccessType.CHANNEL_OWNER, AccessType.CHANNEL_MOD]


