import logging

from twbot.TwitchHandler import TwitchHandler
from utils.json_log import load_config
import asyncio

load_config()
logger = logging.getLogger('krya.twitch')

new_loop = asyncio.new_event_loop()
asyncio.set_event_loop(new_loop)


async def main():
    logger.info("Main start")
    bot = TwitchHandler(loop=new_loop)
    try:
        await bot.start()
    finally:
        logger.info("End of main")

new_loop.run_until_complete(main())
