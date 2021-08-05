from tgbot.events.global_events.GlobalEventFactory import GlobalEventFactory
from tgbot.events.global_events.GlobalEventProcessor import GlobalEventProcessor
from tgbot.constants import TG_TEST_GROUP_ID
from utils.array import get_first
from datetime import datetime
from telethon.utils import get_peer_id


async def process_global_events(event):
    global_events = await event.client.db.get_global_events()
    if global_events is None:
        return

    chat_id: int = int(get_peer_id(event.message.peer_id, add_mark=False))
    channel = await get_first(await event.client.db.get_auth_subchat(chat_id))
    if channel is None:
        return

    if channel['global_events'] == 0:
        return

    for global_event in global_events:
        if TG_TEST_GROUP_ID != chat_id and global_event['active_to'] is not None and global_event['active_to'] < datetime.now():
            event.client.logger.info('Skipping event {} because not active anymore: {}'.format(global_event['event_key'], global_event['active_to']))
            continue

        try:
            processor: GlobalEventProcessor = GlobalEventFactory.get(global_event['event_key'])
            await processor.process(global_event=global_event, event=event, channel=channel)
        except Exception as e:
            event.client.logger.exception(e)
