from utils.log import load_config
from twbot.ChatAdapter import ChatAdapter
import asyncio

load_config()

new_loop = asyncio.new_event_loop()
asyncio.set_event_loop(new_loop)


async def main():
    adapter = ChatAdapter()
    try:
        await adapter.start()
    finally:
        await adapter.disconnect()

new_loop.run_until_complete(main())
