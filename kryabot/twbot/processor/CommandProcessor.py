import asyncio
import random
from datetime import datetime
from typing import List, Dict, Union

from twbot import commandbuilder
from twbot.object.Command import Command
from twbot.object.Channel import Channel
from twbot.object.MessageContext import MessageContext
from twbot.processor.Processor import Processor


class CommandProcessor(Processor):
    def __init__(self):
        super().__init__()

        self.commands: Dict[int, List[Command]] = {}
        self.songs: Dict[int, List[Dict]] = {}
        self.locked_by: int = None

    async def update_song_data(self, channel_id: int = None)->None:
        self.logger.info('Updating data for channel {}'.format(channel_id))
        new_songs = await self.db.getChannelSongs(channel_id=channel_id)
        self.songs = self.init_struct(self.songs, channel_id)
        self.songs = self.add_data(self.songs, new_songs)

        self.logger.debug('Song data: {}'.format(self.songs))

    async def update(self, channel_id: int = None)->None:
        self.logger.info('Updating data for channel {}'.format(channel_id))

        while self.locked_by is not None:
            self.logger.info('In update, locked by {} waiting...'.format(self.locked_by))
            await asyncio.sleep(2)

        if channel_id is not None:
            self.locked_by = channel_id

        try:
            new_commands = await self.db.getChannelCommands(channel_id=channel_id)
            self.logger.debug('Command data raw: {}'.format(new_commands))

            # Update command data
            update_ts = datetime.now()
            for row in new_commands:
                id = int(row['channel_id'])
                if id not in self.commands:
                    self.commands[id] = []

                exists = False
                for cmd in self.commands[id]:
                    if cmd.command_id == int(row['channel_command_id']):
                        cmd.set(row, update_ts)
                        exists = True
                        break

                if not exists:
                    self.commands[id].append(Command(row, update_ts, self.logger))

            if channel_id is not None:
                self.commands[channel_id] = [cmd for cmd in self.commands[channel_id] if not cmd.outdated(update_ts)]

            # Update song data
            await self.update_song_data(channel_id)
        except Exception as ex:
            self.logger.exception(ex)

        if channel_id is not None:
            self.locked_by = None

        self.logger.debug('Command data: {}'.format(self.commands))
        self.ready = True

    async def process(self, context: MessageContext)->None:
        if context.message is None:
            self.logger.error("Received empty message: {}".format(context.stringify()))
            return

        context.message = str(context.message)
        word_list = context.message.split()

        try:
            command = word_list[0].lower()
        except Exception as e:
            return

        user_level = self.get_access_level(context)
        # Global commands
        global_cmd = commandbuilder.build(command_name=command, context=context)
        if global_cmd is not None:
            self.logger.debug('Processing global command {} in channel {} by {}'.format(command, context.channel.channel_name, context.user.name))
            await global_cmd.process()
            return

        # Custom commands
        self.logger.debug('Searching for command {} in channel {}, access {}'.format(command, context.channel.channel_name, user_level))
        cmd = self.find_command(context.channel.channel_id, command, user_level)
        if cmd is None:
            self.logger.debug('Command {} not found'.format(command))
            return

        try:
            await self.process_command(context, cmd)
        except Exception as e:
            self.logger.exception(e)

    def find_command(self, channel_id: int, command_name: str, user_level: int)->Union[Command, None]:
        if channel_id not in self.commands:
            return None

        for cmd in self.commands[channel_id]:
            if cmd.command_name.lower() != command_name.lower():
                continue

            self.logger.debug('Found command {}, checking availability'.format(cmd.command_name))
            if not cmd.active:
                self.logger.debug('Not active')
                return None

            if not cmd.can_access(user_level):
                self.logger.debug('No access for user level {}'.format(user_level))
                return None

            if not cmd.can_use():
                self.logger.debug('On cooldown')
                return None

            cmd.used()
            return cmd

        return None

    def find_command_trigger(self, channel_id: int)->Union[Command, None]:
        if channel_id not in self.commands:
            return None

        for cmd in self.commands[channel_id]:
            if not cmd.active:
                continue

            if not cmd.can_trigger():
                continue

            cmd.triggered()
            return cmd

        return None

    def find_song(self, channel_id: int)->Dict:
        if channel_id not in self.songs:
            return {}

        for cmd in self.songs[channel_id]:
            return cmd

        return {}

    async def process_command(self, context: MessageContext, command: Command)-> None:
        if context.user is None:
            name = ''
            content = ''
        else:
            name = context.user.name
            content = context.message

        reply_text = await self.replace_keywords(context.channel, command, name, content)
        self.logger.debug('Processing command {} in channel {}: {}'.format(command.command_name, context.channel.channel_name, reply_text))
        if reply_text is None or len(reply_text) == 0:
            return

        await context.reply(reply_text)
        await self.db.updateCommandUsage(command.command_id)

    async def process_trigger(self, channel: Channel)->None:
        cmd = self.find_command_trigger(channel_id=channel.channel_id)
        if cmd is None:
            # self.logger.debug('Failed to find command to trigger in channel {}'.format(channel.channel_name))
            return

        context = MessageContext(None)
        context.channel = channel

        self.logger.debug('Found command {} to trigger in channel {}'.format(cmd.command_name, channel.channel_name))
        try:
            await self.process_command(context, cmd)
            channel.triggered()
        except Exception as e:
            self.logger.exception(e)

    def get_access_level(self, context: MessageContext)->int:
        if context.user.name.lower() == 'kuroskas':
            return 9

        # if await self.is_admin(irc_data.author.name) is True:
        #     return 8

        if context.user.name == context.channel.channel_name:
            return 7

        if context.is_mod is True:
            return 6

        # if irc_data.author.is_vip is True:
        #     return 5

        if context.is_subscriber is True:
            return 2

        return 0

    def get_message_word(self, message, index: int)->str:
        try:
            return message.split()[index]
        except:
            return ''

    async def replace_keywords(self, channel: Channel, cmd: Command, sender_name: str, text: str):
        after_text = ' '.join(text.split(' ')[1:]).strip()
        answer = cmd.message
        answer = answer.replace('#user#', sender_name)
        answer = answer.replace('#target#', self.get_message_word(text, 1))
        answer = answer.replace('#w1#', self.get_message_word(text, 1))
        answer = answer.replace('#w2#', self.get_message_word(text, 2))
        answer = answer.replace('#w3#', self.get_message_word(text, 3))
        answer = answer.replace('#w4#', self.get_message_word(text, 4))
        answer = answer.replace('#w5#', self.get_message_word(text, 5))
        answer = answer.replace('#context#', after_text if after_text != '' else cmd.additional_text or '')
        answer = answer.replace('#channel#', channel.channel_name)
        answer = answer.replace('#used#', str(cmd.usages))

        if '#song#' in answer:
            song = await self.get_song_data(channel)
            if song is None or song == '':
                return ''
            answer = answer.replace('#song#', song)

        if '#online#' in answer:
            answer = answer.replace('#online#', await channel.get_online_count())

        if '#uptime#' in answer:
            answer = answer.replace('#uptime#', await channel.get_uptime_formatted())

        while '#randomviewer#' in answer:
            answer = answer.replace('#randomviewer#', await channel.get_random_viewer(), 1)

        for i in range(1, 10):
            max_val = i * 10
            key = '#randomnumber{}#'.format(max_val)
            if key in answer:
                answer = answer.replace(key, self.get_random_number(max_val=max_val))

        return answer

    async def get_song_data(self, channel: Channel)->str:
        song = self.find_song(channel_id=channel.channel_id)
        if song == {}:
            return ''

        try:
            if song['source'] == 'vk':
                return await self.api.get_vk_song(song['key'])
            if song['source'] == 'spotify':
                return ''
        except Exception as ex:
            self.logger.exception(ex)

        return ''

    def get_random_number(self, max_val: int = 100, min_val: int = 1)->str:
        val = random.randint(min_val, max_val)
        return str(val)
