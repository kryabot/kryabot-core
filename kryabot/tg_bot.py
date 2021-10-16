#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from utils.json_log import load_config
import logging
import asyncio
from tgbot.LoopContainer import LoopContainer

load_config()
logger = logging.getLogger('krya.tg')


async def main():
    while True:
        container = None
        try:
            container = LoopContainer()
            await container.start()
            await container.run()
        except (KeyboardInterrupt, SystemExit):
            logger.error('Loop container force exit, stopping processes')
            await container.stop()
            break
        except Exception as ex:
            logger.exception(ex)
            logger.error('Main loop container failed, restarting in 10 seconds')
            await asyncio.sleep(10)
            continue

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
