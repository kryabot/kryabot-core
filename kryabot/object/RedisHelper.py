import asyncio
import aioredis
import logging
from utils.json_parser import json_to_dict, dict_to_json


class RedisHelper:
    def __init__(self, host, port, password, loop=None, minsize=2, maxsize=40):
        self.host = host
        self.port = port
        self.password = password
        self.minsize = minsize
        self.maxsize = maxsize
        self.loop = loop
        self.redis_pool = None
        self.logger = logging.getLogger('krya.db')
        self.listener = None
        self.receiver = None
        self.event_triggers = []

    async def connection_init(self):
        self.logger.info('Opening redis connection')
        address = (self.host, self.port)
        self.redis_pool = await aioredis.create_redis_pool(address=address,
                                                     password=self.password,
                                                     minsize=self.minsize,
                                                     maxsize=self.maxsize,
                                                     loop=self.loop,
                                                     encoding='utf-8')

    async def start_listener(self, initial_subscribes=None):
        # Already started
        if self.listener is not None:
            return

        if self.redis_pool is None:
            await self.connection_init()

        self.receiver = aioredis.pubsub.Receiver(loop=self.loop)
        with await self.redis_pool as conn:
            self.listener = conn

            if initial_subscribes is not None:
                await initial_subscribes()

            async for channel, msg in self.receiver.iter():
                func = None
                for method in self.event_triggers:
                    if method['topic'].encode() == channel.name:
                        func = method['func']

                if func is not None:
                    try:
                        await func(json_to_dict(msg))
                    except Exception as ex:
                        self.logger.exception(ex)
                        self.logger.info('Exception during callback: {}'.format(func))
                else:
                    self.logger.error('Callable function not found for ' + str(channel.name))

    async def subscribe_event(self, topic, func):
        if self.listener is None:
            self.logger.info('Can not subscribe if listener not started! (topic={})'.format(topic))
            raise Exception(f'Can not subscribe if listener not started!')

        self.logger.info('Redis topic subscribe: ' + topic)
        await self.listener.subscribe(self.receiver.channel(topic))
        self.event_triggers.append({'topic': topic, 'func': func})

    async def publish_event(self, topic, data):
        if self.redis_pool is None:
            await self.connection_init()

        with await self.redis_pool as conn:
            return await conn.publish(topic, dict_to_json(data))

    async def get_value_by_key(self, key):
        if self.redis_pool is None:
            await self.connection_init()

        with await self.redis_pool as conn:
            return await conn.execute('get', key)

    async def set_value_by_key(self, key, val, expire=None):
        if self.redis_pool is None:
            await self.connection_init()

        with await self.redis_pool as conn:
            if expire is None or expire <= 0:
                return await conn.set(key, val)
            else:
                return await conn.setex(key=key, value=val, seconds=expire)

    async def add_to_list(self, list_name, value, expire=None):
        if self.redis_pool is None:
            await self.connection_init()

        with await self.redis_pool as conn:
            await conn.sadd(list_name, value)
            if expire:
                await conn.expire(list_name, expire)

    async def get_list_members(self, list_name):
        if self.redis_pool is None:
            await self.connection_init()

        with await self.redis_pool as conn:
            return await conn.execute('smembers', list_name)

    async def put_dict(self, key, obj):
        if self.redis_pool is None:
            await self.connection_init()

        with await self.redis_pool as conn:
            return await conn.execute('hmset', key, obj)

    async def get_next_index(self, index_name):
        if self.redis_pool is None:
            await self.connection_init()

        with await self.redis_pool as conn:
            return await conn.execute("incr", index_name)

    async def delete(self, key):
        if self.redis_pool is None:
            await self.connection_init()

        with await self.redis_pool as conn:
            return await conn.delete(key)

    async def delete_by_pattern(self, pattern):
        if self.redis_pool is None:
            await self.connection_init()
        with await self.redis_pool as conn:
            keys = await conn.keys(pattern)

            if not keys:
                return

            for key in keys:
                await conn.delete(key)

    # Method with parsing
    async def get_parsed_value_by_key(self, key):
        data = await self.get_value_by_key(key=key)
        return json_to_dict(data)

    async def set_parsed_value_by_key(self, key, val, expire=None):
        data = dict_to_json(val)
        return await self.set_value_by_key(key, data, expire)

    async def get_parsed_list_members(self, list):
        datas = await self.get_list_members(list_name=list)
        return_array = []
        for data in datas:
            return_array.append(json_to_dict(data))

        return return_array

    async def add_to_list_parsed(self, list_name, data, expire=None):
        json_data = dict_to_json(data)
        return await self.add_to_list(list_name=list_name, value=json_data, expire=expire)

    async def key_exists(self, key):
        if self.redis_pool is None:
            await self.connection_init()
        with await self.redis_pool as conn:
            return await conn.exists(key)

    async def push_list_to_right(self, list_name, data)->int:
        return await self.push_to_list(list_name, data, True)

    async def push_list_to_left(self, list_name, data)->int:
        return await self.push_to_list(list_name, data, False)

    async def push_to_list(self, list_name, data, to_right=True)->int:
        key = "rpush" if to_right else "lpush"

        if self.redis_pool is None:
            await self.connection_init()

        with await self.redis_pool as conn:
            return await conn.execute(key, list_name, data)

    async def get_one_from_list(self, list_name, first=True):
        key = "lpop" if first else "rpop"

        if self.redis_pool is None:
            await self.connection_init()

        with await self.redis_pool as conn:
            return await conn.execute(key, list_name)

    async def get_one_from_list_parsed(self, list_name, first=True):
        data = await self.get_one_from_list(list_name, first)
        return json_to_dict(data)
