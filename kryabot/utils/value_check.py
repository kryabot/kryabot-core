async def avoid_none(value):
    if value is None:
        return ''
    return value


async def is_empty_string(value):
    return value is None or value == ''


async def map_kick_setting(key):
    if key == 'not_verified':
        return 'Kick non-verified users: '
    if key == 'not_sub':
        return 'Kick non-subs: '
    if key == 'not_active':
        return 'Kick deleted accounts: '
    if key == 'not_follower':
        return 'Kick non-followers: '
    return key


async def get_json_value(key, data):
    if key in data:
        return data[key]

    return None