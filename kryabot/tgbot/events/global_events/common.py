from tgbot.events.global_events.HalloweenEventProcessor import HalloweenEventProcessor
from tgbot.events.global_events.easter import process_easter
from tgbot.constants import TG_TEST_GROUP_ID
from utils.array import get_first
from datetime import datetime


async def process_global_events(event):
    global_events = await event.client.db.get_global_events()
    if global_events is None:
        return

    channel = await get_first(await event.client.db.get_auth_subchat(event.message.to_id.channel_id))
    if channel is None:
        return

    if channel['global_events'] == 0:
        return

    for global_event in global_events:
        if TG_TEST_GROUP_ID != event.message.to_id.channel_id and global_event['active_to'] is not None and global_event['active_to'] < datetime.now():
            event.client.logger.info('Skipping event {} because not active anymore: {}'.format(global_event['event_key'], global_event['active_to']))
            continue

        if global_event['event_key'] == 'easter':
            await process_easter(global_event, event, channel)
        elif global_event['event_key'] == 'halloween2020':
            processor = HalloweenEventProcessor.get_instance()
            await processor.process(global_event, event, channel)
        else:
            event.client.logger.error('Received unknown global event key: {}'.format(global_event['event_key']))
