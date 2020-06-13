from enum import Enum


class OrderedEnum(Enum):
    def __ge__(self, other):
        if self.__class__ is other.__class__:
            return self.value >= other.value
        return NotImplemented

    def __gt__(self, other):
        if self.__class__ is other.__class__:
            return self.value > other.value
        return NotImplemented

    def __le__(self, other):
        if self.__class__ is other.__class__:
            return self.value <= other.value
        return NotImplemented

    def __lt__(self, other):
        if self.__class__ is other.__class__:
            return self.value < other.value
        return NotImplemented


class UserAccess(OrderedEnum):
    UNKNOWN = 0     # Wrong channel, errors, any other unknown issues
    NOT_VERIFIED = 1
    VERIFIED = 2
    FOLLOWER = 3
    SUBSCRIBER = 4
    CHAT_ADMIN = 5
    CHAT_SUDO = 6
    CHAT_OWNER = 8
    SUPPORTER = 9
    SUPER_ADMIN = 10