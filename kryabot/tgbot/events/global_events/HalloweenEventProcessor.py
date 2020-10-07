import asyncio
from datetime import datetime

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

    async def is_active_event(self, client)->bool:
        global_events = await client.db.get_global_events()

        halloween_event = None
        for event in global_events:
            if event['event_key'] == 'halloween2020':
                halloween_event = event

        if halloween_event is None:
            return False

        if halloween_event['active_to'] is not None and halloween_event['active_to'] < datetime.now():
            return False

        if halloween_event['active_from'] is not None and halloween_event['active_from'] > datetime.now():
            return False

        return True

    async def update_channels(self, client):
        try:
            tg_channels = await client.db.get_auth_subchats()
            for tg_channel in tg_channels:
                if tg_channel['tg_chat_id'] == 0:
                    continue

                if tg_channel['global_events'] == 1:
                    if not tg_channel['tg_chat_id'] in self.channels.channels:
                        client.logger.info("Created HalloweenChannel for {}".format(tg_channel['tg_chat_id']))
                        self.channels.new_channel(tg_channel['tg_chat_id'], tg_channel['bot_lang'])
                else:
                    if tg_channel['tg_chat_id'] in self.channels.channels:
                        client.logger.info("Removing HalloweenChannel for {}".format(tg_channel['tg_chat_id']))
                        self.channels.remove_channel(tg_channel['tg_chat_id'])
        except Exception as ex:
            self.get_logger().exception(ex)

    async def pumpkin_spawner(self, client):
        if not await self.is_active_event(client):
            return

        client.logger.info('Starting pumpkin_spawner')
        while True:
            await asyncio.sleep(600)

            try:
                if not await self.is_active_event(client):
                    return

                await self.update_channels(client)

                for key in self.channels.channels.keys():
                    count = int(await client.get_group_member_count(int(key)))
                    if self.channels.channels[key].can_spawn_regular(count):
                        await self.channels.channels[key].spawn_regular(client, count)
                    elif self.channels.channels[key].can_spawn_boss(count):
                        await self.channels.channels[key].spawn_boss(client, count)
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

        if target_message.sender_id != event.client.me.id:
            return

        sender = await get_first(await event.client.db.getUserByTgChatId(event.message.sender_id))
        if sender is None:
            event.client.logger.info('Skipping event because sender user record not found: {}'.format(event.message.sender_id))
            return

        if HalloweenConfig.is_event_boss(target_message):
            await self.process_boss(event_data, event, channel, target_message, sender)
        elif HalloweenConfig.is_event_regular(target_message):
            await self.process_regular(event_data, event, channel, target_message, sender)
        else:
            return

    async def process_regular(self, event_data, event, channel, target_message, sender):
        client = event.client

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

        destroyed = False
        try:
            destroyed = self.channels.hit_pumkin(event.message.to_id.channel_id, target_message.id, sender['user_id'])
            await target_message.delete()
        except Exception as ex:
            self.get_logger().exception(ex)

        if not destroyed:
            return

        await client.db.add_currency_to_user(HalloweenConfig.currency_key, sender['user_id'], 1)

        currency_data = await get_first(await client.db.get_user_currency_amount(HalloweenConfig.currency_key, sender['user_id']))
        sender_entity = await client.get_entity(event.message.sender_id)
        sender_label = await format_html_user_mention(sender_entity)

        text = client.translator.getLangTranslation(channel['bot_lang'], 'GLOBAL_HALLOWEEN_PUMPKIN_DESTROY')
        text = text.format(user=sender_label, total=int(currency_data['amount']))
        text += ' 👻'

        info_message = await event.reply(text)

        try:
            await event.delete()
        except Exception as ex:
            self.get_logger().exception(ex)

        # await asyncio.sleep(60)
        # await info_message.delete()

    async def process_boss(self, event_data, event, channel, target_message, sender):
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

        try:
            self.channels.add_for_deletion(event.message.to_id.channel_id, event.message.id)
            if self.channels.hit_pumkin(event.message.to_id.channel_id, target_message.id, sender['user_id']):
                await target_message.delete()
        except Exception as ex:
            self.get_logger().exception(ex)

        # try:
        #     await event.delete()
        # except Exception as ex:
        #     self.get_logger().exception(ex)

