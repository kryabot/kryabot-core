from utils.log import load_config
from twbot.Bot import Bot
import asyncio

load_config()

new_loop = asyncio.new_event_loop()
asyncio.set_event_loop(new_loop)


async def main():
    bot = Bot(loop=new_loop)
    await bot.start()

new_loop.run_until_complete(main())
