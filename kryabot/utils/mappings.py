from telethon.tl.types import UserStatusRecently, UserStatusEmpty, UserStatusLastMonth, UserStatusOffline, UserStatusLastWeek, UserStatusOnline


def status_to_text(status)->str:
    if status is None:
        return 'USER_STATUS_UNKNOWN'

    if isinstance(status, UserStatusRecently):
        return 'USER_STATUS_RECENTLY'

    if isinstance(status, UserStatusEmpty):
        return 'USER_STATUS_UNKNOWN'

    if isinstance(status, UserStatusLastMonth):
        return 'USER_STATUS_LAST_MONTH'

    if isinstance(status, UserStatusOffline):
        return 'USER_STATUS_OFFLINE'

    if isinstance(status, UserStatusLastWeek):
        return 'USER_STATUS_LAST_WEEK'

    if isinstance(status, UserStatusOnline):
        return 'USER_STATUS_ONLINE'

    return 'USER_STATUS_UNKNOWN'
