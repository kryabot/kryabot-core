from telethon import events
from telethon.tl.types import InputMediaUploadedDocument, DocumentAttributeAudio, PeerChat
from tgbot.events.global_events.common import process_global_events
from tgbot.commands.commandbuilder import run
from utils.array import get_first
from tgbot.events.chat_actions import user_join_check, user_left
import aiohttp
import aiofiles

from tgbot.events.moderate import moderate

# Todo: avoid hardcode id (cache? db?)
monitoring_id = 1255287898
owner_id = 766888597

kryabot_audio = None

@events.register(events.NewMessage(func=lambda e: e.is_private))
async def event_private_message(event: events.NewMessage.Event):
    # Currently we are ignoring this data
    pass


@events.register(events.NewMessage(func=lambda e: e.is_group or e.is_channel))
async def event_group_message(event: events.NewMessage.Event):
    if isinstance(event.message.to_id, PeerChat):
        return

    # IF for TEST only
    # if event.message.to_id.channel_id != 1144972862 and event.sender_id != owner_id:
    #     return
    await event.mark_read()
    try:
        await moderate(event, False)
        await process_global_events(event)
    except Exception as ex:
        event.client.logger.exception(event.stringify())
        await event.client.exception_reporter(ex, 'Error in event_group_message event')


@events.register(events.MessageEdited(func=lambda e: e.is_group or e.is_channel))
async def event_group_message_edit(event: events.MessageEdited.Event):
    if isinstance(event.message.to_id, PeerChat):
        return
    # IF for TEST only
    # if event.message.to_id.channel_id != 1144972862 and event.sender_id != owner_id:
    #     return
    await event.mark_read()
    try:
        await moderate(event, True)
    except Exception as ex:
        event.client.logger.exception(event.stringify())
        await event.client.exception_reporter(ex, 'Error in event_group_message_edit event')


@events.register(events.NewMessage(pattern='^/', func=lambda e: e.is_group or e.is_channel))
async def event_group_message_command(event: events.NewMessage.Event):
    # if event.message.to_id.channel_id != 1144972862 and event.sender_id != owner_id:
    #     return
    await event.mark_read()
    try:
        await run(event)
    except Exception as ex:
        event.client.logger.exception(event.stringify())
        await event.client.exception_reporter(ex, 'Error in event_group_message_command event')


@events.register(events.NewMessage(monitoring_id))
async def event_monitoring_message(event: events.NewMessage.Event):
    pass


@events.register(events.ChatAction)
async def event_chat_action(event: events.ChatAction.Event):
    if event.action_message is None:
        event.client.logger.error('Received chat action without action message: {}'.format(event.stringify()))
        return

    channel = await get_first(await event.client.db.get_auth_subchat(event.action_message.to_id.channel_id))
    if channel is None:
        return

    event.client.logger.info(str(event.action_message))
    if event.new_pin is True:
        await process_event_new_pin(event)
    elif event.new_photo is True and event.photo is not None:
        await process_event_new_photo(event)
    elif event.user_joined is True:
        await user_join_check(event.client, channel, event.action_message.sender_id, event.action_message.id)
    elif event.user_added is True:
        await user_join_check(event.client, channel, event.action_message.action.users[0], event.action_message.id)
    elif event.user_left is True:
        await user_left(event.client, channel, event.action_message.sender_id)
    elif event.user_kicked or event.created or event.unpin:
        # Ignored chat actions
        pass
    else:
        # Unknown type
        pass


async def process_event_new_pin(event: events.ChatAction.Event):
    pass


async def process_event_new_photo(event: events.ChatAction.Event):
    pass


async def process_event_new_user(event: events.ChatAction.Event):
    pass
