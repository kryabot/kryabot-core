from object.BotConfig import BotConfig
from webserver.WebHandler import WebHandler
import asyncio


async def main():
	handler = WebHandler(loop=asyncio.get_event_loop(), cfg=BotConfig())
	await handler.start()
	while True:
		await asyncio.sleep(5)
		print('sleeping')

loop = asyncio.get_event_loop()
loop.run_until_complete(main())