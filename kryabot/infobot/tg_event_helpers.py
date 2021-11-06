import functools

from telethon import events
from telethon.tl.functions.channels import GetParticipantRequest, GetFullChannelRequest
from telethon.tl.functions.messages import GetFullChatRequest
from telethon.tl.types import Channel, Chat, ChannelParticipantCreator, ChannelParticipantAdmin
from utils.array import get_first
from infobot.LinkTable import LinkTable
from infobot.Target import Target
from infobot.TargetLink import TargetLink


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
                if isinstance(event, events.CallbackQuery.Event):
                    await event.answer('Only group admins can change my configuration!', alert=True)
                return

            return await func(event, *args)
        return wrapped
    return wrapper


def required_infobot():
    def wrapper(func):
        @functools.wraps(func)
        async def wrapped(event, *args):
            infobot_raw = await get_first(await event.client.db.getInfoBotByChat(event.chat_id))
            if not infobot_raw:
                try:
                    channel = await event.client(GetFullChannelRequest(channel=event.chat_id))
                    name = channel.chats[0].title
                except:
                    channel = await event.client(GetFullChatRequest(chat_id=event.chat_id))
                    name = channel.chats[0].title

                await event.client.db.createInfoBot(event.chat_id, name)
                infobot_raw = await get_first(await event.client.db.getInfoBotByChat(event.chat_id))

            return await func(event, Target(infobot_raw), *args)
        return wrapped
    return wrapper


# Most be used together with required_infobot(), because expects infobot as input param
def required_infobot_link():
    def wrapper(func):
        @functools.wraps(func)
        async def wrapped(event, infobot: Target, *args):
            if not isinstance(event, events.CallbackQuery.Event):
                # Interested only in callback queries (button presses)
                return

            data = event.query.data.decode().split(':')
            link_table: LinkTable = LinkTable(data[1])

            try:
                infobot.selected_id = int(data[2])
            except IndexError:
                pass

            if link_table == LinkTable.TWITCH:
                infobot_links = await event.client.db.getInfobotTwitchLinks(infobot.id)
            # elif link_table == LinkTable.BOOSTY:
            #     infobot_links = await event.client.db.getInfobotLinksByType(infobot.id, link_table.value)
            else:
                infobot_links = await event.client.db.getInfobotLinksByType(infobot.id, link_table.value)

            for link_raw in infobot_links:
                infobot.selected_links.append(TargetLink(link_raw, None))

            return await func(event, infobot, *args)
        return wrapped
    return wrapper
