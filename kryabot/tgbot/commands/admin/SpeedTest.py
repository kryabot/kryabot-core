from datetime import datetime, timezone
from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand


class SpeedTest(BaseCommand):
    command_names = ['speedtest']
    access_level = UserAccess.SUPER_ADMIN

    def __init__(self, event, parsed):
        super().__init__(event, parsed, SpeedTest.access_level)

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return

        text = ''
        started_at = datetime.now(tz=timezone.utc)
        diff = started_at - self.event.message.date
        text += 'Telegram: {}\n'.format(diff.total_seconds())

        started_at = datetime.now(tz=timezone.utc)
        test = await self.db.getChannelNotices()
        diff =  datetime.now(tz=timezone.utc) - started_at
        text += 'Database: {}\n'.format(diff.total_seconds())

        started_at = datetime.now(tz=timezone.utc)
        test = await self.db.get_stream_flows(104717035)
        diff = datetime.now(tz=timezone.utc) - started_at
        text += 'Cache: {}\n'.format(diff.total_seconds())

        started_at = datetime.now(tz=timezone.utc)
        test = await self.client.api.twitch.check_channel_following(104717035, 175355403)
        diff = datetime.now(tz=timezone.utc) - started_at
        text += 'Twitch: {}\n'.format(diff.total_seconds())

        started_at = datetime.now(tz=timezone.utc)
        test = await self.client.api.vk.get_song('likasaxon')
        diff = datetime.now(tz=timezone.utc) - started_at
        text += 'VK: {}\n'.format(diff.total_seconds())

        await self.event.reply(text)