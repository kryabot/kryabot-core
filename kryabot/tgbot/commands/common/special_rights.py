from telethon.tl.types import PeerUser
from utils.value_check import avoid_none


async def add_special_right(right_type, cmd):
    user_db = await cmd.event.client.db.getUserByTgChatId(cmd.reply_message.from_id)
    if user_db is None or len(user_db) == 0:
        await cmd.reply_fail(cmd.get_translation('CMD_ADDSPECIAL_NOT_VERIFIED'))
        return

    if await cmd.is_chatsudo(user_db[0]['user_id'], cmd.reply_message.from_id):
        await cmd.reply_fail(cmd.get_translation('CMD_ADDSPECIAL_IS_SUDO'))
        return

    user = await cmd.client.get_entity(PeerUser(cmd.reply_message.from_id))
    admin_user = await cmd.client.get_entity(PeerUser(cmd.event.message.from_id))



    try:
        text = await cmd.get_text_after_command()
    except:
        text = ''

    if right_type == 'WL':
        await cmd.db.addUserToWhitelist(cmd.channel['channel_id'],
                                          user_db[0]['user_id'],
                                          cmd.reply_message.from_id,
                                          await avoid_none(user.first_name),
                                          await avoid_none(user.last_name),
                                          await avoid_none(user.username),
                                          cmd.event.message.from_id,
                                          text)
        await cmd.reply_success(cmd.get_translation('CMD_ADDVIP_SUCCESS'))
    elif right_type == 'BL':
        await cmd.db.addUserToBlacklist(cmd.channel['channel_id'],
                                          user_db[0]['user_id'],
                                          cmd.reply_message.from_id,
                                          await avoid_none(user.first_name),
                                          await avoid_none(user.last_name),
                                          await avoid_none(user.username),
                                          cmd.event.message.from_id,
                                          text)
        await cmd.client.kick_user_from_channel(cmd.event.message.to_id, cmd.reply_message.from_id, cmd.channel['ban_time'])
        await cmd.reply_success(cmd.get_translation('CMD_ADDBAN_SUCCESS'))
    elif right_type == 'SUDO':
        await cmd.db.addUserToSudo(cmd.channel['channel_id'],
                                          user_db[0]['user_id'],
                                          cmd.reply_message.from_id,
                                          await avoid_none(user.first_name),
                                          await avoid_none(user.last_name),
                                          await avoid_none(user.username),
                                          cmd.event.message.from_id,
                                          text)
        await cmd.reply_success(cmd.get_translation('CMD_ADDSUDO_SUCCESS'))

    await cmd.client.init_special_rights(cmd.channel['channel_id'])

    await cmd.client.report_to_monitoring(
        '[{chn}]\n User {afn} {aln} {au} {aid} added {rt} right to user {tfn} {tln} {tu} {tid}'.format(
            chn=cmd.channel['channel_name'],
            afn=await avoid_none(admin_user.first_name),
            aln=await avoid_none(admin_user.last_name),
            au=await avoid_none(admin_user.username),
            aid=await avoid_none(cmd.event.message.from_id),
            rt=right_type,
            tfn=await avoid_none(user.first_name),
            tln=await avoid_none(user.last_name),
            tu=await avoid_none(user.username),
            tid=await avoid_none(cmd.reply_message.from_id),
        ))
