import asyncio
import logging
from datetime import datetime

from object.Base import Base
from object.RedisHelper import RedisHelper
from object.System import System
from utils import redis_key


class Pinger(Base):
    def __init__(self, system: System, logger: logging, redis: RedisHelper):
        self.system: System = system
        self.logger: logging = logger
        self.redis: RedisHelper = redis

    async def run_task(self):
        self.logger("Created pinger task for {}".format(self.system))
        await self.redis.set_value_by_key(key=redis_key.get_general_startup(str(self.system.value)), val=self.get_body())

        while True:
            try:
                await self.redis.set_value_by_key(key=redis_key.get_general_ping(str(self.system.value)), val=1, expire=redis_key.ttl_minute * 2)
            except Exception as ex:
                self.logger.exception(ex)

            await asyncio.sleep(60)

    def get_body(self):
        return {"when": datetime.utcnow()}

    async def monitor_pings(self):
        pass