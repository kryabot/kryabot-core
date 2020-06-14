import asyncio
import os
import logging
from typing import Dict, List

from telethon.errors import ChannelPrivateError
from telethon.extensions import html
from telethon.tl.functions.channels import GetParticipantRequest, GetFullChannelRequest
from telethon.tl.functions.messages import GetFullChatRequest
from telethon.tl.types import UpdateChannel, UpdateNewChannelMessage, MessageService, MessageActionChatDeleteUser, \
    MessageActionChatAddUser, UpdateNewMessage, UpdateChatParticipants, InputMediaPhotoExternal

from telethon import TelegramClient, events, Button

from infobot import Event
from infobot.Target import Target
from infobot.instagram.InstagramEvents import InstagramPostEvent, InstagramStoryEvent
from infobot.twitch.TwitchEvents import TwitchEvent
from object.Translator import Translator
from utils import redis_key


@events.register(events.NewMessage(pattern='/ping'))
async def pong(event):
    await event.reply('pong')


@events.register(events.NewMessage(pattern='/link', func=lambda e: not e.is_private))
async def link(event):
    words = event.raw_text.split(' ')
    if len(words) != 2:
        event.client.logger.debug('Incorrect use of command: {}'.format(event.raw_text))
        return

    infos = await event.client.db.getAllNewInfoBots()

    user_info = None
    for info in infos:
        if info['auth_key'] == words[1]:
            user_info = info

    if user_info is None:
        event.client.logger.debug('Received auth key {} but no records found'.format(words[1]))
        return

    if user_info['target_id'] is not None:
        event.client.logger.debug('Cannot link because infobot {} already linked to {}'.format(user_info['infobot_id'], user_info['target_id']))
        return

    username = None

    try:
        channel = await event.client(GetFullChannelRequest(channel=event.chat_id))
        username = channel.chats[0].username
    except:
        channel = await event.client(GetFullChatRequest(chat_id=event.chat_id))

    event.client.logger.debug(channel.stringify())
    event.client.logger.info('event.chat_id = {}'.format(event.chat_id))
    name = channel.chats[0].title
    await event.client.db.updateInfoTargetData(user_info['infobot_id'], event.chat_id, name, username)

    reporter = await event.client.db.getResponseByUserId(int(user_info['user_id']))
    if reporter is None or len(reporter) == 0:
        event.client.logger.debug('Failed to report link status to user ID {}'.format(user_info['user_id']))
        return

    reporter = reporter[0]
    event.client.logger.debug(reporter)
    await event.client.send_message(int(reporter['tg_id']), 'Successfully linked "{}"!'.format(name))


@events.register(events.NewMessage(pattern='/unlink', func=lambda e: e.is_private))
async def unlink(event):
    user_record = await event.client.db.getUserByTgChatId(event.message.from_id)
    if user_record is None or len(user_record) == 0:
        event.client.logger.debug('Unauthorized unlink attempt from user {}'.format(event.message.from_id))
        return

    user_record = user_record[0]
    info = await event.client.db.getInfoBotByUser(user_record['user_id'])
    if info is None or len(info) == 0:
        event.client.logger.debug('Info record not found for user ID {}'.format(user_record['user_id']))
        return

    info = info[0]
    await event.client.db.updateInfoTargetData(info['infobot_id'], None, None, None)
    await event.reply('Unlink successful')


@events.register(events.Raw)
async def raw(event):
    event.client = event._client
    print(event.stringify())

    if isinstance(event, UpdateChatParticipants):
        print('Skipping UpdateChatParticipants')
        return

    if isinstance(event, UpdateChannel):
        try:
            participant = await event.client(GetParticipantRequest(channel=event.channel_id, user_id=event.client.me.id))
            channel = await event.client(GetFullChannelRequest(channel=event.channel_id))
        except ChannelPrivateError:
            participant = None
            channel = None

        if participant:
            if channel.chats[0].username:
                print('Added to public channel ', event.channel_id, channel.chats[0].username)
            else:
                print('Added to private channel', event.channel_id)
            print(channel.stringify())
        else:
            print('Removed from channel', event.channel_id)
        return

    if isinstance(event, UpdateNewMessage) and isinstance(event.message, MessageService):
        if isinstance(event.message.action, MessageActionChatAddUser) and event.client.me.id in event.message.action.users:
            print('I was added to chat ', event.message.to_id.chat_id)
        if isinstance(event.message.action, MessageActionChatDeleteUser) and event.client.me.id == event.message.action.user_id:
            print('I was removed from chat ', event.message.to_id.chat_id)

        return

    # if isinstance(event, UpdateNewChannelMessage):
    #     if isinstance(event.message, MessageService):
    #         if isinstance(event.message.action, MessageActionChatDeleteUser) and event.message.action.user_id == event.client.me.id:
    #             print('I was deleted from group')
    #             return
    #         elif isinstance(event.message.action, MessageActionChatAddUser) and event.client.me.id in event.message.action.users:
    #             print('I was added to group')
    #             return
    #         else:
    #             print('still unknown')


    #print(event.stringify())

class KryaInfoBot(TelegramClient):
    def __init__(self, manager):
        self.db = manager.db
        self.cfg = manager.cfg
        self.manager = manager
        self.me = None
        self.logger = logging.getLogger('krya.infobot')
        self.translator: Translator = None

        # Path to session file
        path = os.getenv('SECRET_DIR')
        if path is None:
            path = ''

        super().__init__(path + 'info_bot_session', base_logger=self.logger, api_id= self.cfg.getTelegramConfig()['API_ID'], api_hash=self.cfg.getTelegramConfig()['API_HASH'])
        self._parse_mode = html

    async def run(self, wait=False):
        self.logger.debug('Starting TG info bot')
        self.add_event_handler(pong)
        self.add_event_handler(link)
        self.add_event_handler(unlink)
        #self.add_event_handler(raw)

        self.translator = Translator(await self.db.getTranslations(), self.logger)

        await self.start(bot_token=self.cfg.getTelegramConfig()['INFO_BOT_API_KEY'])
        self.me = await self.get_me()
        print(self.me)

        if wait:
            await self.run_until_disconnected()

    async def info_event(self, targets: List[Target], event: Event):
        if isinstance(event, InstagramPostEvent):
            await self.instagram_post_event(targets, event)
        elif isinstance(event, InstagramStoryEvent):
            await self.instagram_story_event(targets, event)
        elif isinstance(event, TwitchEvent):
            await self.twitch_stream_event(targets, event)
        else:
            raise ValueError('Received unsupported event type: ' + str(type(event)))

    async def instagram_post_event(self, targets: List[Target], event: InstagramPostEvent):
        await event.save(self.db)
        files = []

        if event.media_list:
            for media in event.media_list:
                file = await self.manager.api.twitch.download_file_io(media.video_url or media.url)
                file.seek(0)
                files.append(file)

        if files:
            message = None
            for target in targets:
                if not message:
                    await self.send_file(entity=target.target_id, file=files, caption=event.get_formatted_text(), parse_mode='html')
                else:
                    await self.send_file(entity=target.target_id, file=message.media, caption=event.get_formatted_text(), parse_mode='html')

    async def instagram_story_event(self, targets: List[Target], event: InstagramStoryEvent):
        await event.save(self.db)

        for item in reversed(event.items):
            media = None
            for target in targets:
                btn = None

                if item.external_url:
                    btn = Button.url(self.translator.getLangTranslation(target.lang, 'INSTA_STORY_SWIPE_BUTTON'), url=item.external_url)
                    btn = [btn]

                if item.is_video:
                    if not media:
                        message = await self.send_file(entity=target.target_id, file=item.video_url, buttons=btn)
                        media = message.media
                    else:
                        await self.send_file(entity=target.target_id, file=media, buttons=btn)
                else:
                    if not media:
                        file = await self.manager.api.twitch.download_file_io(item.url)
                        file.seek(0)
                        message = await self.send_file(entity=target.target_id, file=file, buttons=btn)
                        media = message.media
                    else:
                        await self.send_file(entity=target.target_id, file=media, buttons=btn)

    async def twitch_stream_event(self, targets: List[Target], event: TwitchEvent):
        url = event.get_formatted_image_url()
        file = None
        button = None

        text_key = 'TWITCH_NOTIFICATION_START'
        if event.recovery:
            return
        elif event.update:
            text_key = 'TWITCH_NOTIFICATION_UPDATE'
            file = InputMediaPhotoExternal(url)
            button = [Button.url(event.profile.twitch_name, url=event.get_channel_url())]
        elif event.down:
            text_key = 'TWITCH_NOTIFICATION_FINISH'
        elif event.start:
            file = InputMediaPhotoExternal(url)
            button = [Button.url(event.profile.twitch_name, url=event.get_channel_url())]
            text_key = 'TWITCH_NOTIFICATION_START'

        for target in targets:
            if event.update and not target.twitch_update:
                continue
            if event.start and not target.twitch_start:
                continue
            if event.down and not target.twitch_end:
                continue

            text = self.translator.getLangTranslation(target.lang, text_key)
            await self.send_message(target.target_id, message=text, file=file, buttons=button, link_preview=False)
