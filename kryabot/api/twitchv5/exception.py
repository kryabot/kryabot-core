from typing import Dict


class TwitchException(Exception):
    match_text: str = None

    def __init__(self, body: Dict):
        self.error: str = body.get('error', '')
        self.status: int = body.get('status', 0)
        self.message: str = body.get('message', '')

    @classmethod
    def matches(cls, body: Dict) -> bool:
        return cls.match_text and cls.match_text in body['message']


class AlreadyBannedError(TwitchException):
    match_text: str = 'user_id field is already banned'


class AddVipRequestNoAvailableVipSlots(TwitchException):
    match_text: str = 'Unable to add VIP. Visit the Achievements page'


class UnvipRequestTargetNotVip(TwitchException):
    match_text: str = 'The specified user is not a VIP'


class ExpiredAuthToken(TwitchException):
    pass

