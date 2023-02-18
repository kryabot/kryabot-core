import asyncio

from models.dao.TwitchMessage import TwitchMessage
from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand
from datetime import datetime, timedelta
from scrape.twitch_message_history import replicate_messages


class Random(BaseCommand):
    command_names = ['random']
    access_level = UserAccess.CHAT_ADMIN
    semaphore = asyncio.Semaphore(1)

    def __init__(self, event, parsed):
        super().__init__(event, parsed, Random.access_level)

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return

        if await self.db.is_cooldown_random(self.channel['tg_chat_id'], self.sender['user_id']):
            return

        await self.db.set_random_cooldown(self.channel['tg_chat_id'], self.sender['user_id'])

        async with Random.semaphore:
            try:
                await self.replicate_messages()
            except Exception as err:
                self.logger.exception(err)

        message: TwitchMessage = await TwitchMessage.getRandomUserMessageInChannel(channel_id=self.channel['tw_id'], user_id=self.sender['tw_id'])
        if message:
            await self.event.reply('{}: {}\n\n{}'.format(self.sender['name'], message.text, message.sent_at))
        else:
            await self.reply_fail("Sorry, failed to find message for you!")

    async def replicate_messages(self):
        # Check last existing message
        # avoid fetching if last message was within 7 days
        latest: TwitchMessage = await TwitchMessage.getLatestUserMessageInChannel(channel_id=self.channel['tw_id'], user_id=self.sender['tw_id'])
        if latest and datetime.utcnow() - latest.sent_at > timedelta(days=7):
            return

        broadcaster = await self.db.getUserRecordByTwitchId(self.channel['tw_id'])
        if not broadcaster or not broadcaster[0]:
            self.logger.error("Failed to find user record by twitch id: {}".format(self.channel['tw_id']))
            return

        await replicate_messages(channel_name=broadcaster[0]['name'], user_id=self.sender['tw_id'])