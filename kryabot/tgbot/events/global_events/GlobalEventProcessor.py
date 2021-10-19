import logging
import math
from datetime import datetime, timedelta
from typing import Dict

from object.Base import Base
from tgbot.constants import TG_TEST_GROUP_ID


class GlobalEventProcessor(Base):
    instance = None
    name = ''

    def __init__(self):
        self.event_name: str = None
        self.startup_tasks: [] = []
        self.channels: EventChannels = EventChannels(EventChannel)
        self.required_members = 20
        self.required_messages_total = 0
        self.required_messages_interval = 0

    @classmethod
    def get_instance(cls):
        if cls.instance is None:
            cls.instance = cls()

        return cls.instance

    async def process(self, **args):
        raise NotImplemented

    def get_logger(self)->logging:
        return logging.getLogger('krya.tg')

    async def get_event(self, client):
        global_events = await client.db.get_global_events()
        event = next(filter(lambda e: e['event_key'] == self.event_name, global_events), None)
        return event

    async def is_active_event(self, client)->bool:
        event = await self.get_event(client)

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
        event = await self.get_event(client)

        try:
            tg_channels = await client.db.get_auth_subchats()
            for tg_channel in tg_channels:
                if tg_channel['tg_chat_id'] == 0:
                    await self.remove_channel(tg_channel)
                    continue

                if tg_channel['auth_status'] == 0:
                    await self.remove_channel(tg_channel)
                    continue

                if event['public'] != 1 and tg_channel['tg_chat_id'] != TG_TEST_GROUP_ID:
                    await self.remove_channel(tg_channel)
                    continue

                count = int(await client.get_group_member_count(int(tg_channel['tg_chat_id'])))
                if count < self.required_members:
                    client.logger.info('Skipping event for channel {} because not enough members: {}'.format(tg_channel['tg_chat_id'], count))
                    await self.remove_channel(tg_channel)
                    continue

                if self.required_messages_total and self.required_messages_total > 0:
                    counted_messages = 0
                    try:
                        history = await client.db.getTgHistoricalStats(tg_channel['channel_id'], 'message', self.required_messages_interval + 2)
                        if history:
                            iterated = 0
                            for item in history:
                                if iterated >= self.required_messages_interval:
                                    break
                                counted_messages += min(item['count'], math.floor(self.required_messages_total / 2))
                                iterated += 1
                    except Exception as historyEx:
                        self.get_logger().exception(historyEx)

                    if counted_messages < self.required_messages_total:
                        self.get_logger().info('Skipping event for channel {} because not enough chat activity {}'.format(tg_channel['tg_chat_id'], counted_messages))
                        await self.remove_channel(tg_channel)
                        continue

                if tg_channel['global_events'] != 1:
                    await self.remove_channel(tg_channel)
                    continue

                await self.add_channel(tg_channel)
        except Exception as ex:
            self.get_logger().exception(ex)

    async def add_channel(self, tg_channel):
        if not tg_channel['tg_chat_id'] in self.channels.channels:
            self.get_logger().info("Created event channel for {}".format(tg_channel['tg_chat_id']))
            self.channels.create(tg_channel['tg_chat_id'], tg_channel['bot_lang'])

    async def remove_channel(self, tg_channel):
        if tg_channel['tg_chat_id'] in self.channels.channels:
            self.get_logger().info("Removing event channel for {}".format(tg_channel['tg_chat_id']))
            self.channels.remove(tg_channel['tg_chat_id'])

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
