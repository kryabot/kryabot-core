import traceback
import os
import logging
from typing import List, Union

from telethon.errors import ChannelPrivateError, WebpageCurlFailedError, BotCommandInvalidError
from telethon.extensions import html
from telethon import functions, types
from telethon.tl.functions.channels import GetParticipantRequest, GetFullChannelRequest
from telethon.tl.types import UpdateChannel, MessageService, MessageActionChatDeleteUser, \
    MessageActionChatAddUser, UpdateNewMessage, UpdateChatParticipants, InputMediaPhotoExternal

from telethon import TelegramClient, events, Button

from infobot import Event
from infobot.Target import Target, InfobotLang
from infobot.TargetLink import TargetLink
from infobot.boosty.BoostyEvents import BoostyEvent
from infobot.instagram.InstagramEvents import InstagramPostEvent, InstagramStoryEvent
from infobot.twitch.TwitchEvents import TwitchEvent
from object.Pinger import Pinger
from object.System import System
from object.Translator import Translator
from scrape.scrape_word_cloud import get_word_cloud_screenshot
from infobot.tg_events import register_events
from tgbot import constants
from utils.formatting import td_format


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
        self.translator: Translator = Translator.getInstance()

        # Path to session file
        path = os.getenv('SECRET_DIR')
        if path is None:
            path = ''

        super().__init__(path + 'info_bot_session', base_logger=self.logger, api_id= self.cfg.getTelegramConfig()['API_ID'], api_hash=self.cfg.getTelegramConfig()['API_HASH'], flood_sleep_threshold=300)
        self._parse_mode = html
        self.loop.create_task(Pinger(System.INFOBOT_TELEGRAM, self.logger, self.db.redis).run_task())
        self.translator.setLogger(self.logger)

    async def refresh_translations(self):
        self.translator.push(await self.db.getTranslations())

    async def run(self, wait=False):
        self.logger.debug('Starting TG info bot')
        await self.connect()
        self.me = await self.get_me()

        register_events(self)
        await self.refresh_translations()
        await self.register_commands()
        await self.start(bot_token=self.cfg.getTelegramConfig()['INFO_BOT_API_KEY'])
        if wait:
            await self.run_until_disconnected()

    async def register_commands(self):
        # Commands available only to admins to resetting only admins scopes
        for supported_bot_lang in InfobotLang:
            try:
                await self(functions.bots.ResetBotCommandsRequest(
                    lang_code=supported_bot_lang.value,
                    scope=types.BotCommandScopeChatAdmins(),
                ))
                # Commands for default, any user in anywhere
                # await self(functions.bots.SetBotCommandsRequest(
                #     scope=types.BotCommandScopeDefault(),
                #     lang_code=supported_bot_lang.value,
                #     commands=[])
                # )

                # Admins in chats and supergroups
                await self(functions.bots.SetBotCommandsRequest(
                    scope=types.BotCommandScopeChatAdmins(),
                    lang_code=supported_bot_lang.value,
                    commands=[
                        types.BotCommand(command='follow', description=self.translator.getLangTranslation(supported_bot_lang.value, 'IB_CMDINFO_FOLLOW')),
                        types.BotCommand(command='following', description=self.translator.getLangTranslation(supported_bot_lang.value, 'IB_CMDINFO_FOLLOWING')),
                    ])
                )
            except BotCommandInvalidError as ex:
                self.logger.error('Failed to refresh commands for language {}'.format(supported_bot_lang.value))
                self.logger.exception(ex)

    async def exception_reporter(self, err, info):
        await self.report_to_monitoring(message='Error: {}: {}\n\n{}\n\n<pre>{}</pre>'.format(type(err).__name__, err, info, ''.join(traceback.format_tb(err.__traceback__))), avoid_err=True)

    async def report_to_monitoring(self, message, avoid_err=False):
        # avoid_err used to avoid infinitive loop on reporting fail
        try:
            await self.send_message(constants.TG_GROUP_MONITORING_ID, message)
        except Exception as err:
            if avoid_err is False:
                raise err

    async def info_event(self, links: List[TargetLink], event: Event):
        try:
            if isinstance(event, InstagramPostEvent):
                await self.instagram_post_event(links, event)
            elif isinstance(event, InstagramStoryEvent):
                await self.instagram_story_event(links, event)
            elif isinstance(event, TwitchEvent):
                await self.twitch_stream_event(links, event)
            elif isinstance(event, BoostyEvent):
                await self.boosty_post_event(links, event)
            else:
                raise ValueError('Received unsupported event type: ' + str(type(event)))
        except Exception as ex:
            await self.exception_reporter(ex, 'For event {} in targets {}'.format(type(event), links))

    async def instagram_post_event(self, links: List[TargetLink], event: InstagramPostEvent):
        files = []
        self.logger.info('Sending instagram post event')

        if event.media_list:
            for media in event.media_list:
                file = await self.manager.api.twitch.download_file_io(media.video_url or media.url)
                file.seek(0)
                files.append(file)

        self.logger.info('Sending instagram post event after getting files')
        
        if files:
            message = None
            for link in links:
                try:
                    if not message:
                        await self.send_file(entity=link.target.target_id, file=files, caption=event.get_formatted_text())
                    else:
                        await self.send_file(entity=link.target.target_id, file=message.media, caption=event.get_formatted_text())
                except ChannelPrivateError:
                    await self.report_to_monitoring('ChannelPrivateError. Target ID: {}, tg ID: {}'.format(link.target.id, link.target.target_id), True)
                except Exception as ex:
                    await self.exception_reporter(ex, 'instagram_post_event')

    async def instagram_story_event(self, links: List[TargetLink], event: InstagramStoryEvent):
        for item in event.items:
            media = None

            self.logger.info('Formatting mentions for caption')
            caption = ''
            if item.mentions:
                for mention in item.mentions:
                    caption += event.get_mention_link(mention) + '\n'
                caption += '\n'

            caption += event.get_link_to_profile()
            self.logger.info('Caption formatted')
            for link in links:
                btns = None
                self.logger.info('Sending to user {}'.format(link.target.user_id))
                try:
                    if item.external_urls:
                        btns = []
                        for url in item.external_urls:
                            btn = Button.url(self.translator.getLangTranslation(link.target.get_lang(), 'INSTA_STORY_SWIPE_BUTTON'), url=url)
                            btns.append(btn)

                    if item.is_video:
                        if not media:
                            message = await self.send_file(entity=link.target.target_id, caption=caption, file=item.video_url, buttons=btns)
                            media = message.media
                        else:
                            await self.send_file(entity=link.target.target_id, file=media, caption=caption, buttons=btns)
                    else:
                        if not media:
                            file = await self.manager.api.twitch.download_file_io(item.image_url)
                            file.seek(0)
                            message = await self.send_file(entity=link.target.target_id, file=file, caption=caption, buttons=btns)
                            media = message.media
                        else:
                            await self.send_file(entity=link.target.target_id, file=media, caption=caption, buttons=btns)
                except ChannelPrivateError:
                    await self.report_to_monitoring('ChannelPrivateError. Target ID: {}, tg ID: {}'.format(link.target.id, link.target.target_id), True)
                except Exception as ex:
                    await self.exception_reporter(ex, 'instagram_story_event')

    async def twitch_stream_event(self, links: List[TargetLink], event: TwitchEvent):
        self.logger.info('Stream: {}, start={}, update={}, down={}, recovery={}'.format(event.profile.twitch_name, event.start, event.update, event.finish, event.recovery))
        url = event.get_formatted_image_url()
        file = None
        button = None

        text_key = 'TWITCH_NOTIFICATION_START'
        if event.finish:
            text_key = 'TWITCH_NOTIFICATION_FINISH'
            try:
                file = await self.generate_twitch_word_cloud_image(event)
            except Exception as ex:
                self.logger.exception(ex)
        elif event.recovery:
            text_key = 'TWITCH_NOTIFICATION_RECOVERY'
            button = [Button.url(event.profile.twitch_name, url=event.get_channel_url())]
        elif event.update:
            text_key = 'TWITCH_NOTIFICATION_UPDATE'
            file = InputMediaPhotoExternal(url)
            button = [Button.url(event.profile.twitch_name, url=event.get_channel_url())]
        elif event.start:
            file = InputMediaPhotoExternal(url)
            button = [Button.url(event.profile.twitch_name, url=event.get_channel_url())]
            text_key = 'TWITCH_NOTIFICATION_START'

        for link in links:
            if event.update and not link.config.get_field_value('show_update'):
                continue
            if event.start and not link.config.get_field_value('show_start'):
                continue
            if event.finish and not link.config.get_field_value('show_end'):
                continue

            base_text = self.translator.getLangTranslation(link.target.get_lang(), text_key)
            text = ''
            if event.recovery:
                text = base_text.format(event.profile.twitch_name)
            elif event.update:
                for upd in event.updated_data:
                    if 'title' in upd:
                        text += '\n{} <b>{}</b>'.format(self.translator.getLangTranslation(link.target.get_lang(), 'TWITCH_NOTIFICATION_UPDATED_TITLE'), event.title)
                    if 'game' in upd:
                        text += '\n{} <b>{}</b>'.format(self.translator.getLangTranslation(link.target.get_lang(), 'TWITCH_NOTIFICATION_UPDATED_GAME'), event.game_name)

                text = '{}\n{}'.format(base_text, text)
            elif event.start:
                text = '<b>{}</b>\n🎮{}\n\n{}'.format(event.title, event.game_name, base_text)
            elif event.finish:
                try:
                    text = await self.format_stream_finish_message(link.target, event)
                except Exception as ex:
                    self.logger.exception(ex)
                    # Fall-back to general one-liner text
                    text = base_text.format(event.profile.twitch_name)

            try:
                try:
                    event_message = await self.send_message(link.target.target_id, message=text, file=file, buttons=button, link_preview=False, parse_mode='html')
                    if event.start and not event.recovery and link.config.get_field_value('pin_start'):
                        await event_message.pin(notify=True)
                except WebpageCurlFailedError:
                    fileio = await self.manager.api.twitch.download_file_io(file.url)
                    fileio.seek(0)
                    fileio.filename = "image.jpg"
                    await self.send_message(link.target.target_id, message=text, file=fileio, buttons=button, link_preview=False, parse_mode='html')
            except ChannelPrivateError:
                await self.report_to_monitoring('ChannelPrivateError. Target ID: {}, TG ID: {}'.format(link.target.id, link.target.target_id), True)
            except Exception as ex:
                await self.exception_reporter(ex, 'twitch_stream_event')

    async def boosty_post_event(self, links: List[TargetLink], event: BoostyEvent):
        max_length = 1000

        button = [Button.url('View full post  👀', url=event.get_post_url())]
        text = '<b>New boosty post!</b>'

        if event.title:
            text += '\n\n{}'.format(event.title)

        if event.get_text():
            text += '\n\n{}'.format(event.get_text())

        text = (text[:max_length] + '...') if len(text) > max_length else text

        if event.access_name:
            text += '\n\nAccess level: <b>{}</b>'.format(event.access_name)

        for link in links:

            try:
                if event.videos:
                    for video in event.videos:
                        await self.send_file(link.target.target_id, file=video, link_preview=False, parse_mode='html')

                if event.images:
                    await self.send_file(link.target.target_id, caption=text, file=InputMediaPhotoExternal(event.images[0]), buttons=button, link_preview=False, parse_mode='html')
                else:
                    await self.send_message(link.target.target_id, message=text, buttons=button, link_preview=False, parse_mode='html')
            except ChannelPrivateError:
                await self.report_to_monitoring('ChannelPrivateError. Target ID: {}, tg ID: {}'.format(link.target.id, link.target.target_id), True)
            except Exception as ex:
                await self.exception_reporter(ex, 'boosty_post_event')

    async def format_stream_finish_message(self, target, event) -> str:
        formatted_message = '⏹ ' + self.translator.getLangTranslation(target.get_lang(), 'TWITCH_NOTIFICATION_FINISH').format(event.profile.twitch_name)

        label_played = self.translator.getLangTranslation(target.get_lang(), 'IB_NOTIFICATION_TWITCH_PLAYED')
        label_break = self.translator.getLangTranslation(target.get_lang(), 'IB_NOTIFICATION_TWITCH_TECHNICAL_BREAK')

        channels = await self.db.get_channel_by_twitch_id(event.profile.twitch_id)
        if channels is None or len(channels) == 0:
            return formatted_message

        for item in event.summary:
            item['ts'] = item['ts'].replace(tzinfo=None)

        stream_start = None
        stream_end = None
        game_changes = ''
        previous_item = None
        contains_changes = False
        last_resume_ts = None
        for item in event.summary:
            if item['type'] == 'start':
                stream_start = item['ts']
            elif item['type'] == 'finish':
                # Possible multiple finishes, interested in last one
                stream_end = item['ts']
                calc_from = last_resume_ts if last_resume_ts and last_resume_ts > previous_item['ts'] else previous_item['ts']
                game_changes += '\n🎮 {} <b>{}</b>\n({})'.format(label_played, previous_item['new_value'], td_format(stream_end - calc_from))
            elif item['type'] == 'resume':
                contains_changes = True
                last_resume_ts = item['ts']
                game_changes += '\n🎮 {}\n({})'.format(label_break, td_format(item['ts'] - stream_end))
            else:
                # Game change
                if previous_item:
                    contains_changes = True
                    calc_from = last_resume_ts if last_resume_ts and last_resume_ts > previous_item['ts'] else previous_item['ts']
                    game_changes += '\n🎮 {} <b>{}</b>\n({})'.format(label_played, previous_item['new_value'], td_format(item['ts'] - calc_from))
                previous_item = item

        stream_duration = stream_end - stream_start
        formatted_message += '\n' + game_changes

        if contains_changes:
            formatted_message += '\n\n🎮 {}: {}'.format(self.translator.getLangTranslation(target.get_lang(), 'IB_NOTIFICATION_TWITCH_DURATION'), td_format(stream_duration))

        formatted_message += '\n'
        active_chatters = await self.db.getChatMostActiveUser(channels[0]['channel_id'], stream_duration.seconds)
        if active_chatters and len(active_chatters) > 0:
            formatted_message += '\n💥 {}'.format(self.translator.getLangTranslation(target.get_lang(), 'IB_NOTIFICATION_TWITCH_MESSAGE_MOST').format(active_chatters[0]['dname'], active_chatters[0]['count']))

        message_count = await self.db.getChatMessageCount(channels[0]['channel_id'], stream_duration.seconds)
        if message_count and len(message_count) > 0 and 'total' in message_count[0]:
            formatted_message += '\n💥 {}'.format(self.translator.getLangTranslation(target.get_lang(), 'IB_NOTIFICATION_TWITCH_MESSAGE_TOTAL').format(message_count[0]['total']))

        return formatted_message

    async def generate_twitch_word_cloud_image(self, event) -> Union[bytes, None]:
        skip_words = ['а', 'у', 'я', 'не', 'с', 'на', 'в', 'это', 'как', 'что', 'из', 'же', 'ну', 'за', 'бы', 'под']

        channels = await self.db.get_channel_by_twitch_id(event.profile.twitch_id)
        if channels is None or len(channels) == 0:
            return None

        rows = await self.manager.db.searchTwitchMessages(channels[0]['channel_id'], '%')
        if rows is None or rows == () or len(rows) == 0:
            raise ValueError("Not enough messages to generate word cloud (rows)")

        words = {}
        request_data = ""
        for record in rows:
            line = record['message']
            word_list = line.split(' ')
            for word in word_list:
                # Skip username tags
                if str(word).startswith('@'):
                    continue

                # Skip short words which does not give value
                if str(word).lower() in skip_words:
                    continue

                if word in words.keys():
                    words[word] += 1
                else:
                    words[word] = 1

        sorted_words = dict(sorted(words.items(), key=lambda item: item[1], reverse=True))

        i = 0
        for word in sorted_words.keys():
            # Word limit 200
            if i >= 200:
                break
            i += 1
            request_data += '{}\t{}\n'.format(sorted_words[word], word)

        if i == 0:
            raise ValueError("Not enough messages to generate word cloud (i)")

        return await get_word_cloud_screenshot(request_data)
