import functools
from telethon.tl.functions.channels import GetParticipantRequest, GetFullChannelRequest
from telethon.tl.functions.messages import GetFullChatRequest
from telethon.tl.types import UpdateChannel, MessageService, MessageActionChatDeleteUser, \
    MessageActionChatAddUser, UpdateNewMessage, UpdateChatParticipants, InputMediaPhotoExternal, Channel, Chat, \
    ChannelParticipantCreator, ChannelParticipantAdmin
from utils.array import get_first


async def is_group_admin(event) -> bool:
    chat = await event.get_chat()
    is_user_admin: bool = False

    if isinstance(chat, Channel):
        participant = await event.client(GetParticipantRequest(channel=chat, participant=event.sender_id))
        is_user_admin = isinstance(participant.participant, (ChannelParticipantCreator, ChannelParticipantAdmin))
    elif isinstance(chat, Chat):
        # In chats, everyone is admin
        is_user_admin = True
    else:
        event.client.logger.error('unknown chat instance type: {}'.format(type(chat)))

    return is_user_admin


def required_admin():
    def wrapper(func):
        @functools.wraps(func)
        async def wrapped(event, *args):
            if not(await is_group_admin(event)):
                return

            return await func(event, *args)
        return wrapped
    return wrapper


def required_infobot():
    def wrapper(func):
        @functools.wraps(func)
        async def wrapped(event, *args):
            infobot = await get_first(await event.client.db.getInfoBotByChat(event.chat_id))
            if not infobot:
                try:
                    channel = await event.client(GetFullChannelRequest(channel=event.chat_id))
                    name = channel.chats[0].title
                except:
                    channel = await event.client(GetFullChatRequest(chat_id=event.chat_id))
                    name = channel.chats[0].title

                await event.client.db.createInfoBot(event.chat_id, name)
                infobot = await get_first(await event.client.db.getInfoBotByChat(event.chat_id))

            # infobot_links = await event.client.db.getInfobotLinks(infobot['infobot_id'])
            return await func(event, infobot, *args)
        return wrapped
    return wrapper