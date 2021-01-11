import logging
from datetime import datetime, timedelta
from typing import Dict

from object.Base import Base

class GlobalEventProcessor(Base):
    instance = None
    name = ''

    def __init__(self):
        self.event_name: str = None
        self.startup_tasks: [] = []
        self.channels: EventChannels = EventChannels(EventChannel)

    @classmethod
    def get_instance(cls):
        if cls.instance is None:
            cls.instance = cls()

        return cls.instance

    async def process(self, **args):
        raise NotImplemented

    def get_logger(self)->logging:
        return logging.getLogger('krya.tg')

    async def is_active_event(self, client)->bool:
        global_events = await client.db.get_global_events()

        event = None
        for raw_event in global_events:
            if raw_event['event_key'] == self.event_name:
                event = raw_event

        if event is None:
            return False

        if event['active_to'] is not None and event['active_to'] < datetime.now():
            return False

        if event['active_from'] is not None and event['active_from'] > datetime.now():
            return False

        return True

    def register_task(self, task):
        self.startup_tasks.append(task)

    def create_tasks(self, client):
        for task in self.startup_tasks:
            client.loop.create_task(task(client))

    async def update_channels(self, client):
        try:
            tg_channels = await client.db.get_auth_subchats()
            for tg_channel in tg_channels:
                if tg_channel['tg_chat_id'] == 0:
                    continue

                if tg_channel['global_events'] == 1:
                    if not tg_channel['tg_chat_id'] in self.channels.channels:
                        client.logger.info("Created event channel for {}".format(tg_channel['tg_chat_id']))
                        self.channels.create(tg_channel['tg_chat_id'], tg_channel['bot_lang'])
                else:
                    if tg_channel['tg_chat_id'] in self.channels.channels:
                        client.logger.info("Removing event channel for {}".format(tg_channel['tg_chat_id']))
                        self.channels.remove(tg_channel['tg_chat_id'])
        except Exception as ex:
            self.get_logger().exception(ex)


class EventChannels(Base):
    def __init__(self, channel_class):
        self.channel_class = channel_class
        self.channels: Dict[int, self.channel_class] = {}

    def create(self, channel_id: int, lang: str):
        self.channels[channel_id] = self.channel_class(channel_id, lang)

    def remove(self, channel_id: int):
        if channel_id in self.channels:
            self.channels.pop(channel_id)

    def get(self, channel_id: int):
        return self.channels[channel_id]

    def get_logger(self)->logging:
        return logging.getLogger('krya.tg')


class EventChannel(Base):
    def __init__(self, channel_id: int, channel_lang: str):
        self.channel_id: int = channel_id
        self.lang: str = channel_lang
        self.last_spawn: datetime = None

    def can_spawn(self)->bool:
        return self.last_spawn is None or self.last_spawn + timedelta(minutes=5) < datetime.utcnow()

    def get_logger(self)->logging:
        return logging.getLogger('krya.tg')
