import asyncio
from datetime import datetime
from typing import List

from tgbot.constants import TG_TEST_GROUP_ID
from tgbot.events.global_events.GlobalEventProcessor import GlobalEventProcessor
from tgbot.events.global_events.HalloweenType import HalloweenChannels, HalloweenConfig
from utils.array import get_first
from utils.formatting import format_html_user_mention


class HalloweenEventProcessor(GlobalEventProcessor):
    name = "halloween2020"

    def __init__(self, ):
        super().__init__()
        self.channels: HalloweenChannels = HalloweenChannels()
        self.get_logger().info("Created HalloweenEventProcessor")

    async def pumpkin_spawner(self, client):
        client.logger.info('Starting pumpkin_spawner')
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
            self.channels.new_channel(tg_channel['tg_chat_id'], tg_channel['bot_lang'])

        while True:
            await asyncio.sleep(600)

            try:
                for key in self.channels.channels.keys():
                    count = await client.get_group_member_count(int(key))
                    if self.channels.channels[key].can_spawn_regular(count):
                        await self.channels.channels[key].spawn_regular(client)
                    elif self.channels.channels[key].can_spawn_boss(count):
                        await self.channels.channels[key].spawn_boss(client)

                    await asyncio.sleep(3)
            except Exception as ex:
                client.logger.exception(ex)

    async def process(self, event_data, event, channel) -> None:
        if not event.message.is_reply:
            return

        if not HalloweenConfig.is_event_reply(event.message):
            return

        target_message = await event.message.get_reply_message()
        if target_message is None:
            return

        if target_message.from_id != event.client.me.id:
            return

        try:
            if not self.channels.is_active(event.message.to_id.channel_id, target_message.id):
                try:
                    await event.delete()
                except:
                    pass

                event.client.logger.info('Skipping because message ID {} in channel {} is not active!'.format(target_message.id, event.message.to_id.channel_id))
                return
        except:
            pass

        sender = await get_first(await event.client.db.getUserByTgChatId(event.message.from_id))
        if sender is None:
            event.client.logger.info('Skipping event because sender user record not found: {}'.format(event.message.from_id))
            return

        self.get_logger().info(target_message.stringify())

        if HalloweenConfig.is_event_boss(target_message):
            await self.process_boss(event_data, event, channel, target_message, sender)
        elif HalloweenConfig.is_event_regular(target_message):
            await self.process_regular(event_data, event, channel, target_message, sender)
        else:
            return

    async def process_regular(self, event_data, event, channel, target_message, sender):
        client = event.client

        destroyed = False
        try:
            destroyed = self.channels.hit_pumkin(event.message.to_id.channel_id, target_message.id, event.message.from_id)
            await target_message.delete()
        except Exception as ex:
            self.get_logger().exception(ex)

        if not destroyed:
            return

        await client.db.add_currency_to_user(HalloweenConfig.currency_key, sender['user_id'], 1)

        currency_data = await get_first(await client.db.get_user_currency_amount(HalloweenConfig.currency_key, sender['user_id']))
        sender_entity = await client.get_entity(event.message.from_id)
        sender_label = await format_html_user_mention(sender_entity)

        text = client.translator.getLangTranslation(channel['bot_lang'], 'GLOBAL_HALLOWEEN_PUMPKIN_DESTROY')
        text = text.format(user=sender_label, total=int(currency_data['amount']))
        text += ' 👻'

        info_message = await event.reply(text)

        try:
            await event.delete()
        except Exception as ex:
            self.get_logger().exception(ex)

        await asyncio.sleep(60)
        await info_message.delete()

    async def process_boss(self, event_data, event, channel, target_message, sender):
        try:
            if self.channels.hit_pumkin(event.message.to_id.channel_id, target_message.id, event.message.from_id):
                await target_message.delete()
        except Exception as ex:
            self.get_logger().exception(ex)


        try:
            await event.delete()
        except Exception as ex:
            self.get_logger().exception(ex)
