from typing import Dict

from utils.array import get_first
from utils.formatting import format_html_user_mention

currency_key = 'pumpkin'
pumpkin_message: str = "🎃"
punch_message: str = "👊"
expired_list: Dict = {}


async def process_halloween_2020(event_data, event, channel):
    client = event.client

    if not event.message.is_reply:
        return

    if not is_event_reply(event.message.text):
        return

    target_message = await event.message.get_reply_message()
    if not is_event_message(target_message.text):
        return

    if target_message.peer_id != client.me.id:
        client.logger.info('Skipping because pumpkin not sent by bot')
        return

    try:
        if expired_list[channel['channel_id']] == target_message.id:
            try:
                await event.delete()
            except:
                pass

            client.logger.info('Skipping because found message ID in expired_list')
            return
    except:
        pass

    sender = await get_first(await client.db.getUserByTgChatId(event.message.peer_id))
    if sender is None:
        client.logger.info('Skipping event because sender user record not found: {}'.format(event.message.peer_id))
        return

    try:
        expired_list[channel['channel_id']] = target_message.id
        await target_message.delete()
    except:
        pass

    await client.db.add_currency_to_user(currency_key, sender['user_id'], 1)

    currency_data = await get_first(await client.db.get_user_currency_amount(currency_key, sender['user_id']))
    sender_entity = await client.get_entity(event.message.peer_id)
    sender_label = await format_html_user_mention(sender_entity)

    text = client.translator.getLangTranslation(channel['bot_lang'], 'GLOBAL_HALLOWEEN_PUMKIN_DESTROY')
    text = text.format(user=sender_label, total=int(currency_data['amount']))
    text += ' 🥰'

    await event.reply(text)


def is_event_message(text)->bool:
    return text == pumpkin_message


def is_event_reply(text)->bool:
    return text == punch_message
