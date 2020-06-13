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
