from telethon.tl.types import PeerUser
from utils.formatting import format_html_user_mention
from datetime import timedelta, datetime


async def find_reminder(keyword, cmd):
    reminders = await cmd.db.getRemindersByUserId(cmd.channel['user_id'])

    for reminder in reminders:
        if reminder['completed_at'] is None and reminder['reminder_key'].lower() == keyword.lower():
            return reminder

    return None


async def reminder_format_message(event, client, channel, is_auto):
    reminders = await client.db.getRemindersByUserId(channel['user_id'])
    if len(reminders) == 0:
        return
    tg_user = await client.get_entity(PeerUser(event.message.sender_id))

    active_reminders = 0
    completed_reminders = 0
    reply_text = '{user_link}! {text}\n'.format(
        text=client.translator.getLangTranslation(channel['bot_lang'], 'REMINDER_HEADER'),
        user_link=await format_html_user_mention(tg_user))
    for reminder in reminders:
        if reminder['completed_at'] is not None:
            completed_reminders += 1
            continue

        active_reminders += 1
        reply_text += '\n{i}. {txt} [{txt_key}]'.format(i=active_reminders,
                                                        txt=reminder['reminder_text'],
                                                        txt_key=reminder['reminder_key'])

    reply_text += '\n\n' + client.translator.getLangTranslation(channel['bot_lang'], 'REMINDER_COMPLETED').format(
        cmpl=completed_reminders)

    if active_reminders > 0:
        if is_auto is True:
            await client.db.updateLastReminder(channel['channel_subchat_id'])
            await client.db.get_auth_subchat(channel['tg_chat_id'], True)
        await event.reply(reply_text, link_preview=False)


async def reminder_check(event, channel):
    if channel['last_reminder'] is None:
        return

    if channel['reminder_cooldown'] is None or channel['reminder_cooldown'] == 0:
        return

    sender = await event.client.db.getUserByTgChatId(event.message.sender_id)
    if len(sender) == 0:
        return

    if sender[0]['user_id'] != channel['user_id']:
        return

    # Cooldown in hours
    next_redminer_after = channel['last_reminder'] + timedelta(hours=channel['reminder_cooldown'])
    if datetime.now() < next_redminer_after:
        return

    # Cooldown is down, we can remind now
    await reminder_format_message(event, event.client, channel, True)
