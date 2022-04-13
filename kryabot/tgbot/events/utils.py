def is_valid_channel(channel, check_global_events: bool=False) -> bool:
    if channel is None:
        return False

    if channel['tg_chat_id'] == 0:
        return False

    if check_global_events and channel['global_events'] == 0:
        return False

    if channel['auth_status'] == 0:
        return False

    if channel['force_pause'] == 1:
        return False

    return True