import asyncio
from random import randint
from utils.array import get_first
from utils.formatting import format_html_user_mention

cache_cooldown_key = 'easter'
reward_currency_key = 'egg_demo'
counter_currency_key = 'egg_tries'


async def process_easter(event_data, tg_event, channel):
    client = tg_event.client

    if not tg_event.message.is_reply:
        return

    if not is_event_message(tg_event.message.text):
        return

    target_message = await tg_event.message.get_reply_message()
    if not is_event_message(target_message.text):
        return

    if await client.db.is_global_event_cooldown(tg_event.message.to_id.channel_id, tg_event.message.sender_id, cache_cooldown_key):
        await tg_event.message.delete()
        client.logger.debug('Skipping event because of cooldown: {} - {}'.format(tg_event.message.to_id.channel_id, tg_event.message.sender_id))
        return

    await client.db.set_global_event_cooldown(tg_event.message.to_id.channel_id, tg_event.message.sender_id, cache_cooldown_key, event_data['cd'])

    sender = await get_first(await client.db.getUserByTgChatId(tg_event.message.sender_id))
    if sender is None:
        client.logger.debug('Skipping event because sender user record not found: {}'.format(tg_event.message.sender_id))
        return

    if target_message.sender_id == tg_event.message.sender_id:
        client.logger.debug('Skipping event because sender replied to himself: {}'.format(tg_event.message.sender_id))
        return

    target_user = await get_first(await client.db.getUserByTgChatId(target_message.sender_id))
    if target_user is None:
        client.logger.debug('Skipping event because target user record not found: {}'.format(target_message.sender_id))
        return

    to_event_data_amount = 0
    from_event_data_amount = 0

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

    if from_event_data_amount > 0:
        await client.db.add_currency_to_user(reward_currency_key, sender['user_id'], from_event_data_amount)

    if to_event_data_amount > 0:
        await client.db.add_currency_to_user(reward_currency_key, target_user['user_id'], to_event_data_amount)

    # Increase try count by 1
    await client.db.add_currency_to_user(counter_currency_key, sender['user_id'], 1)
    await client.db.add_currency_to_user(counter_currency_key, target_user['user_id'], 1)

    sender_entity = await client.get_entity(tg_event.message.sender_id)
    target_entity = await client.get_entity(target_message.sender_id)

    sender_label = await format_html_user_mention(sender_entity)
    target_label = await format_html_user_mention(target_entity)

    winner_label = ''
    winner_total_wins = 0
    if roll_type == 1:
        winner_label = sender_label
        current_data = await client.db.get_user_currency_amount(counter_currency_key, sender['user_id'])
        winner_total_wins = current_data[0]['amount'] if current_data else 1
    elif roll_type == 2:
        winner_label = target_label
        current_data = await client.db.get_user_currency_amount(counter_currency_key, target_user['user_id'])
        winner_total_wins = current_data[0]['amount'] if current_data else 1

    text = client.translator.getLangTranslation(channel['bot_lang'], 'GLOBAL_EVENT_EASTER_ROLL_{}'.format(roll_type))
    text = text.format(sender=sender_label, target=target_label, winner=winner_label, winner_wins=winner_total_wins if winner_total_wins > 0 else '')

    msg = await tg_event.reply(text)
    await asyncio.sleep(60)
    await msg.delete()


def is_event_message(text)->bool:
    return text == '🥚'