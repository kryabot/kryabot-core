from datetime import datetime, timedelta
from random import randint
from typing import Union

from dateutil.parser import parse

from object.Base import Base
from twbot import ResponseAction
from utils.formatting import td_format


class Channel(Base):

    def __init__(self, db_channel, log, cfg=None, ah=None):
        self.cfg = cfg
        self.ah = ah
        self.raw_data = db_channel
        self.channel_id = self.get_value('channel_id')
        self.channel_name = self.get_value('channel_name')
        self.auto_join = self.get_value('auto_join')
        self.user_id = self.get_value('user_id')
        self.name = self.get_value('name')
        self.tw_id = self.get_value('tw_id')
        self.is_admin = self.get_value('is_admin')
        self.default_notice_text = self.get_value('default_notification')
        self.trigger_period = 30

        self.is_live = False
        self.stream_started = None
        self.prev_stream_started = None
        self.last_stream_down = datetime.now() - timedelta(days=1)
        self.last_trigger_time = self.last_stream_down
        self.last_song_time = self.last_stream_down
        self.last_msg_time = self.last_stream_down
        self.last_chat_activity = self.last_stream_down
        self.recoveries = 0

        self.logger = log

    def get_value(self, atr_name):
        return self.get_attr(self.raw_data, atr_name)

    def update_activity(self):
        self.last_chat_activity = datetime.now()

    async def update_status(self, data, notify=True):
        if notify is True:
            self.logger.info('Processing channel stream update status.')

        if data['down']:
            self.last_stream_down = datetime.now()
            self.is_live = False
            self.prev_stream_started = self.stream_started
            self.stream_started = None
            if notify:
                return '{ch} спасибо за стрим! <3'.format(ch=self.channel_name)

            return None
        elif data['recovery']:
            self.is_live = True
            self.recoveries += 1
        elif data['start']:
            self.is_live = True
            self.stream_started = data['started_at']
            self.recoveries = 0

            if notify:
                return '{ch} удачного тебе стрима <3'.format(ch=self.channel_name)
        elif data['update']:
            if self.stream_started is None:
                self.stream_started = data['started_at']
            self.is_live = True

        return None

    async def get_stream_data(self)->{}:
        try:
            stream_data_new = await self.ah.twitch.get_streams(channel_name=self.channel_name)
            if len(stream_data_new['data']) == 0:
                return None

            return stream_data_new['data'][0]
        except Exception as ex:
            self.logger.exception(ex)
            return None

    async def get_online_count(self)->str:
        data = await self.get_stream_data()
        if data is None or data == {}:
            return '0'

        return str(data['viewer_count'])

    async def get_started_at(self)->Union[datetime, None]:
        data = await self.get_stream_data()
        if data is None or data == {}:
            return None

        return parse(data['started_at'].replace('Z', ''))

    async def get_uptime_formatted(self, offline_label: str = ' Jebaited')->str:
        started_at = await self.get_started_at()
        if started_at is None:
            return offline_label

        diff = datetime.now() - timedelta(hours=3) - started_at
        return td_format(diff)

    async def get_random_viewer(self)->str:
        try:
            data = await self.ah.twitch.get_channel_chatters(self.channel_name)

            data = data['chatters']
            array = data['vips'] + data['moderators'] + data['staff'] + data['admins'] + data['global_mods'] + data['viewers']

            if len(array) == 0:
                return ''

            if len(array) == 1:
                return array[0]

            idx = randint(0, len(array) - 1)
            return array[idx]
        except Exception as ex:
            self.logger.exception(ex)
            return ''

    def can_trigger(self):
        if not self.is_chat_active():
            self.logger.debug('Can not trigger because chat is not active in channel channel {}'.format(self.channel_name))
            return False

        if self.last_trigger_time is None:
            return True

        return datetime.now() > self.last_trigger_time + timedelta(seconds=self.trigger_period)

    def triggered(self):
        self.last_trigger_time = datetime.now()

    def is_chat_active(self, age: int = 300)->bool:
        if self.is_live is True:
            return True

        if self.last_chat_activity is None:
            return False

        return datetime.now() < self.last_chat_activity + timedelta(seconds=age)

    def matches(self, name: str)->bool:
        name = str(name)
        return self.channel_name.lower() == name.lower()

    async def reply(self, message: str):
        await ResponseAction.ResponseMessage.send(self.channel_name, message)

    async def timeout(self, user: str, duration: int, reason: str):
        await ResponseAction.ResponseTimeout.send(channel_name=self.channel_name, user=user, duration=duration, reason=reason)

    async def ban(self, user: str, reason: str):
        await ResponseAction.ResponseBan.send(channel_name=self.channel_name, user=user, reason=reason)
