import logging

from twbot.spamdetector.SpamDetector import SpamDetector
from utils.log import load_config
import asyncio

load_config()
logger = logging.getLogger('krya.spam')

async def main():
    try:
        logger.info('Starting main')
        sd = SpamDetector()
        await sd.init()
        await sd.run()
    except Exception as ex:
        logger.exception(ex)

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
logger.info('End of spam_detector.py')