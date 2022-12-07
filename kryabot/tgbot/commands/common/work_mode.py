async def set_chat_working_mode(cmd, sub_only: bool = False, follow_only: bool = False):
    if sub_only and cmd.channel['join_sub_only']:
        await cmd.reply_fail(cmd.get_translation('CMD_CHATMODE_EXISTS_SUB'))
        return

    if follow_only and cmd.channel['join_follower_only']:
        await cmd.reply_fail(cmd.get_translation('CMD_CHATMODE_EXISTS_FOLLOW'))
        return

    if sub_only is False and follow_only is False and not cmd.channel['join_sub_only'] and not cmd.channel['join_follower_only']:
        await cmd.reply_fail(cmd.get_translation('CMD_CHATMODE_EXISTS_ANY'))
        return

    await cmd.db.updateSubchatMode(cmd.channel['tg_chat_id'], follow_only, sub_only)
    await cmd.reply_success(cmd.get_translation('CMD_CHATMODE_CHANGED'))


async def set_chat_mode_sub(cmd):
    await set_chat_working_mode(cmd, sub_only=True, follow_only=False)


async def set_chat_mode_follow(cmd):
    await set_chat_working_mode(cmd, sub_only=False, follow_only=True)


async def set_chat_mode_any(cmd):
    await set_chat_working_mode(cmd, sub_only=False, follow_only=False)


async def set_chat_kick_mode(cmd, kick_mode: str):
    if not cmd.channel['join_sub_only']:
        await cmd.reply_fail(cmd.get_translation('CMD_KICKMODE_ERROR_NOT_SUBMODE'))
        return

    if cmd.channel['kick_mode'] == kick_mode:
        await cmd.reply_fail(cmd.get_translation('CMD_KICKMODE_ERROR_ALREADY_EXISTS_' + kick_mode.upper()))
        return

    await cmd.db.updateSubchatKickMode(cmd.channel['tg_chat_id'], kick_mode)
    await cmd.reply_success(cmd.get_translation('CMD_CHATMODE_CHANGED_' + kick_mode.upper()))


async def set_chat_kick_mode_period(cmd):
    await set_chat_kick_mode(cmd, 'PERIOD')


async def set_chat_kick_mode_online(cmd):
    await set_chat_kick_mode(cmd, 'ONLINE')
