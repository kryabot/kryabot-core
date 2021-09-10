from telethon.tl.types import PeerChannel
import asyncio

from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand
from infobot import UpdateBuilder
from utils import redis_key


class OnStream(BaseCommand):
    command_names = ['onstream']
    access_level = UserAccess.CHAT_ADMIN

    def __init__(self, event, parsed):
        super().__init__(event, parsed, OnStream.access_level)

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return

        min_value = 0
        max_value = 2
        wait_answer = -1

        channel_entity = await self.client.get_entity(PeerChannel(int(self.channel['tg_chat_id'])))
        sender_id = self.event.message.sender_id

        main_text = self.get_translation('CMD_ON_STREAM_OPTIONS').format(onstream=self.channel['on_stream'])
        answer = wait_answer

        try:
            async with self.client.conversation(channel_entity) as conv:
                question = await conv.send_message(main_text)

                while answer > max_value or answer < min_value:
                    resp = await conv.get_reply(message=question)
                    if resp.sender_id != sender_id:
                        continue
                    try:
                        answer = int(resp.raw_text)
                    except:
                        answer = wait_answer

                await self.db.setSubchatActionOnStream(self.channel['tg_chat_id'], answer)
                await self.reply_success(self.get_translation('CMD_ON_STREAM_SUCCESS'))
        except asyncio.TimeoutError as timeout:
            await self.reply_fail(self.get_translation('CMD_CONV_TIMEOUT'))

        if answer > 0:
            await self.db.registerTwitchProfile(self.channel['user_id'])
            message = UpdateBuilder.TwitchUpdate(UpdateBuilder.UpdateAction.UPDATE, self.channel['user_id'])
            await self.db.redis.publish_event(redis_key.get_infobot_update_profile_topic(), message.to_json())
