from telethon.tl.types import PeerChannel

from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand
import asyncio


class OnRefund(BaseCommand):
    command_names = ['onrefund']
    access_level = UserAccess.CHAT_SUDO

    def __init__(self, event, parsed):
        super().__init__(event, parsed, OnRefund.access_level)

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return

        min_value = 0
        max_value = 5
        wait_answer = -1

        channel_entity = await self.client.get_entity(PeerChannel(int(self.channel['tg_chat_id'])))
        sender_id = self.event.message.sender_id

        main_text = self.get_translation('CMD_ON_REFUND_OPTIONS').format(onref=self.channel['on_refund'])

        try:
            async with self.client.conversation(channel_entity) as conv:
                question = await conv.send_message(main_text)

                answer = wait_answer
                while answer > max_value or answer < min_value:
                    resp = await conv.get_reply(message=question)
                    if resp.sender_id != sender_id:
                        continue
                    try:
                        answer = int(resp.raw_text)
                    except:
                        answer = wait_answer

                await self.db.setSubchatActionOnRefund(self.channel['tg_chat_id'], answer)
                await self.reply_success(self.get_translation('CMD_ON_REFUND_SUCCESS'))
        except asyncio.TimeoutError as timeout:
            await self.reply_fail(self.get_translation('CMD_CONV_TIMEOUT'))
