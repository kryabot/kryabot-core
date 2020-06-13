import asyncio
from random import randint
from utils.array import get_first
from utils.formatting import format_html_user_mention

cache_cooldown_key = 'easter'


async def process_easter(event_data, tg_event, channel):
    client = tg_event.client

    if not tg_event.message.is_reply:
        return

    if not is_event_message(tg_event.message.text):
        return

    target_message = await tg_event.message.get_reply_message()
    if not is_event_message(target_message.text):
        return

    if await client.db.is_global_event_cooldown(tg_event.message.to_id.channel_id, tg_event.message.from_id, cache_cooldown_key):
        await tg_event.message.delete()
        tg_event.client.logger.debug('Skipping event because of cooldown: {} - {}'.format(tg_event.message.to_id.channel_id, tg_event.message.from_id))
        return

    await client.db.set_global_event_cooldown(tg_event.message.to_id.channel_id, tg_event.message.from_id, cache_cooldown_key, event_data['cd'])

    sender = await get_first(await client.db.getUserByTgChatId(tg_event.message.from_id))
    if sender is None:
        client.logger.debug('Skipping event because sender user record not found: {}'.format(tg_event.message.from_id))
        return

    if target_message.from_id == tg_event.message.from_id:
        client.logger.debug('Skipping event because sender replied to himself: {}'.format(tg_event.message.from_id))
        return

    target_user = await get_first(await client.db.getUserByTgChatId(target_message.from_id))
    if target_user is None:
        client.logger.debug('Skipping event because target user record not found: {}'.format(target_message.from_id))
        return

    from_event_data = await get_first(await client.db.getGlobalEventUserDataByEvent(event_data['global_event_id'], sender['user_id']))
    to_event_data = await get_first(await client.db.getGlobalEventUserDataByEvent(event_data['global_event_id'], target_user['user_id']))

    try:
        to_event_data_amount = to_event_data['amount']
    except:
        to_event_data_amount = 0

    try:
        from_event_data_amount = from_event_data['amount']
    except:
        from_event_data_amount = 0

    try:
        to_event_data_val = int(to_event_data['val'])
        to_event_data_val = to_event_data_val + 1
    except:
        to_event_data_val = 1

    try:
        from_event_data_val = int(from_event_data['val'])
        from_event_data_val = from_event_data_val + 1
    except:
        from_event_data_val = 1

    roll = randint(1, 1000)
    roll_type = 0
    if roll < 495:
        from_event_data_amount = from_event_data_amount + 1
        roll_type = 1
        await target_message.delete()
    elif roll < 989:
        to_event_data_amount = to_event_data_amount + 1
        roll_type = 2
        await tg_event.message.delete()
    elif roll < 995:
        await tg_event.message.delete()
        await target_message.delete()
        roll_type = 3
    elif roll < 1001:
        from_event_data_amount = from_event_data_amount + 1
        to_event_data_amount = to_event_data_amount + 1
        roll_type = 4

    await client.db.setGlobalEventDataForUser(event_data['global_event_id'], sender['user_id'], from_event_data_amount, from_event_data_val)
    await client.db.setGlobalEventDataForUser(event_data['global_event_id'], target_user['user_id'], to_event_data_amount, to_event_data_val)


    sender_entity = await client.get_entity(tg_event.message.from_id)
    target_entity = await client.get_entity(target_message.from_id)

    sender_label = await format_html_user_mention(sender_entity)
    target_label = await format_html_user_mention(target_entity)

    winner_label = ''
    winner_total_wins = 0
    if roll_type == 1:
        winner_label = sender_label
        winner_total_wins = from_event_data_amount
    elif roll_type == 2:
        winner_label = target_label
        winner_total_wins = to_event_data_amount

    text = client.translator.getLangTranslation(channel['bot_lang'], 'GLOBAL_EVENT_EASTER_ROLL_{}'.format(roll_type))
    text = text.format(sender=sender_label, target=target_label, winner=winner_label, winner_wins=winner_total_wins if winner_total_wins > 0 else '')

    msg = await tg_event.reply(text)
    await asyncio.sleep(60)
    await msg.delete()


def is_event_message(text)->bool:
    return text == '🥚'