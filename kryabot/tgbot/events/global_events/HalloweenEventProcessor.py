import asyncio
from datetime import datetime
from typing import Dict

from tgbot.constants import TG_TEST_GROUP_ID
from tgbot.events.global_events.GlobalEventProcessor import GlobalEventProcessor
from tgbot.events.global_events.HalloweenType import HalloweenChannel
from utils.array import get_first
from utils.formatting import format_html_user_mention


class HalloweenEventProcessor(GlobalEventProcessor):
    name = "halloween2020"

    def __init__(self):
        super().__init__()
        self.pumpkin_message: str = "🎃"
        self.punch_message: str = "👊"
        self.currency_key: str = "pumpkin"
        self.channels: Dict = {}

    async def pumpkin_spawner(self, client):
        client.logger.info('Starting halloween_pumpkin_spawner')
        global_events = await client.db.get_global_events()

        halloween_event = None
        for event in global_events:
            if event['event_key'] == 'halloween2020':
                halloween_event = event

        if halloween_event is None:
            return

        if halloween_event['active_to'] is not None and halloween_event['active_to'] < datetime.now():
            return

        if halloween_event['active_from'] is not None and halloween_event['active_from'] > datetime.now():
            return

        tg_channels = await client.db.get_auth_subchats()
        for tg_channel in tg_channels:
            if TG_TEST_GROUP_ID != tg_channel['tg_chat_id']:
                continue

            client.logger.info("Created HalloweenChannel for {}".format(tg_channel['tg_chat_id']))
            self.channels[tg_channel['tg_chat_id']] = HalloweenChannel(tg_channel['tg_chat_id'])

        while True:
            await asyncio.sleep(100)

            try:
                for key in self.channels.keys():
                    if self.channels[key].can_spawn():
                        msg = await client.send_message(int(key), self.pumpkin_message)
                        client.logger.info("Spawned pumpkin ID {} in channel {}".format(msg.id, int(key)))
                        self.channels[key].save(msg.id)
            except Exception as ex:
                client.logger.exception(ex)

    async def process(self, event_data, event, channel) -> None:
        client = event.client

        if not event.message.is_reply:
            return

        if not self.is_event_reply(event.message.text):
            return

        target_message = await event.message.get_reply_message()
        if not self.is_event_message(target_message.text):
            return

        if target_message.from_id != client.me.id:
            client.logger.info('Skipping because pumpkin not sent by bot')
            return

        try:
            if not self.channels[event.message.to_id.channel_id].is_active(target_message.id):
                try:
                    await event.delete()
                except:
                    pass

                client.logger.info(
                    'Skipping because message ID {} in channel {} is not active!'.format(target_message.id,
                                                                                         event.message.to_id.channel_id))
                return
        except:
            pass

        sender = await get_first(await client.db.getUserByTgChatId(event.message.from_id))
        if sender is None:
            client.logger.info('Skipping event because sender user record not found: {}'.format(event.message.from_id))
            return

        try:
            self.channels[event.message.to_id.channel_id].set_used(target_message.id)
            await target_message.delete()
        except:
            pass

        await client.db.add_currency_to_user(self.currency_key, sender['user_id'], 1)

        currency_data = await get_first(await client.db.get_user_currency_amount(self.currency_key, sender['user_id']))
        sender_entity = await client.get_entity(event.message.from_id)
        sender_label = await format_html_user_mention(sender_entity)

        text = client.translator.getLangTranslation(channel['bot_lang'], 'GLOBAL_HALLOWEEN_PUMKIN_DESTROY')
        text = text.format(user=sender_label, total=int(currency_data['amount']))
        text += ' 🥰'

        await event.reply(text)

    def is_event_message(self, text) -> bool:
        return text == self.pumpkin_message

    def is_event_reply(self, text) -> bool:
        return text == self.punch_message
