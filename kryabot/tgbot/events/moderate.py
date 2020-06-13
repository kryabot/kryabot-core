from telethon.tl.types import PeerChat
from utils.array import get_first
from tgbot.commands.common.reminders import reminder_check


async def moderate(event, is_edit=False):
    if isinstance(event.message.to_id, PeerChat):
        return

    channel = await get_first(await event.client.db.get_auth_subchat(event.message.to_id.channel_id))
    if channel is None:
        return

    await event.client.db.update_tg_stats_message(channel['tg_chat_id'])
    # Reminder checking
    try:
        if not is_edit:
            await reminder_check(event, channel)
    except Exception as err:
        await event.client.exception_reporter(err, 'Redminer check')

    # media filtering
    try:
        if event.media:
            await event.client.moderation.filter_media(event, channel)
    except Exception as err:
        await event.client.exception_reporter(err, 'Media filtering')

    # Word filtering
    try:
        if event.raw_text is not None and len(event.raw_text) > 0:
            await event.client.moderation.filter_words(channel, event.message)
    except Exception as err:
        await event.client.exception_reporter(err, 'Word filtering')