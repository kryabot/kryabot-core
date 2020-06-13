async def update_chat_entrance(cmd, enabled: bool):
    if enabled and enabled == cmd.channel['enabled_join']:
        await cmd.reply_fail(cmd.get_translation('CMD_ENTRANCE_EXISTS_OPEN'))
        return

    if not enabled and enabled == cmd.channel['enabled_join']:
        await cmd.reply_fail(cmd.get_translation('CMD_ENTRANCE_EXISTS_CLOSED'))
        return

    await cmd.db.updateSubchatEntrance(cmd.channel['tg_chat_id'], enabled)
    if enabled:
        await cmd.reply_success(cmd.get_translation('CMD_ENTRANCE_ENABLED'))
    else:
        await cmd.reply_success(cmd.get_translation('CMD_ENTRANCE_DISABLED'))


async def chat_entrance_enable(cmd):
    await update_chat_entrance(cmd, True)


async def chat_entrance_disable(cmd):
    await update_chat_entrance(cmd, False)
