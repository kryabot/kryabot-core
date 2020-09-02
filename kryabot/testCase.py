import asyncio

from telethon import TelegramClient, events


@events.register(events.ChatAction(func=lambda e: e.action_message is None))
async def chat_action_empty(event: events.ChatAction.Event):
    print(event.stringify())


async def main():
    client = TelegramClient('session_name', 944967, "6a331e0ddd3495e0d1a7e77273225e40")
    client.add_event_handler(chat_action_empty)
    await client.start()
    me = await client.get_me()
    print('Logged in as {} with Telethon version {}'.format(me.username, TelegramClient.__version__))
    await client.run_until_disconnected()

asyncio.get_event_loop().run_until_complete(main())