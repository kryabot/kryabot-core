#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from utils.log import load_config
import logging
import asyncio
from infobot.InfoManager import InfoManager

load_config()
logger = logging.getLogger('krya.infomanager')
logger.setLevel(logging.DEBUG)


async def main():
    while True:
        try:
            print('New manager')
            bot = InfoManager()
            await bot.start()
        except (KeyboardInterrupt, SystemExit):
            logger.error('InfoManager force exit')
            break
        except Exception as ex:
            logger.exception(ex)
            logger.exception('Main InfoManager failed, restarting')
            await asyncio.sleep(60)
            continue

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
