import asyncio
from random import randint

from tgbot.events.global_events.GlobalEventProcessor import GlobalEventProcessor
from tgbot.events.global_events.halloween.HalloweenType import HalloweenChannels, HalloweenConfig
from utils.array import get_first
from utils.formatting import format_html_user_mention
import tgbot.events.global_events.halloween.HalloweenMonsters as HalloweenMonsters


class HalloweenEventProcessor(GlobalEventProcessor):
    def __init__(self, ):
        super().__init__()
        self.event_name = 'halloween'
        self.channels: HalloweenChannels = HalloweenChannels()
        self.get_logger().info("Created HalloweenEventProcessor")
        self.register_task(self.pumpkin_spawner)
        self.required_members = 30
        self.required_messages_total = 100
        self.required_messages_interval = 3

    async def pumpkin_spawner(self, client):
        client.logger.info('Starting pumpkin_spawner')
        delay = 60
        while True:
            await asyncio.sleep(delay)

            try:
                if not await self.is_active_event(client):
                    delay = 600
                    continue

                delay = 60
                await self.update_channels(client)

                for key in self.channels.channels.keys():
                    count = int(await client.get_group_member_count(int(key)))
                    if self.channels.channels[key].can_spawn_number(count):
                        await self.channels.channels[key].spawn_number(client, count)
                    elif self.channels.channels[key].can_spawn_love(count):
                        await self.channels.channels[key].spawn_love_pumpkin(client, count)
                    elif self.channels.channels[key].can_spawn_boss(count):
                        await self.channels.channels[key].spawn_boss(client, count)
                    elif self.channels.channels[key].can_spawn_box(count):
                        await self.channels.channels[key].spawn_box(client, count)
                    elif self.channels.channels[key].can_spawn_scary(count):
                        await self.channels.channels[key].spawn_scary(client, count)
                    elif self.channels.channels[key].can_spawn_silent(count):
                        await self.channels.channels[key].spawn_silent(client, count)
                    elif self.channels.channels[key].can_spawn_regular(count):
                        await self.channels.channels[key].spawn_regular(client, count)
                    await asyncio.sleep(randint(2, 15))
            except Exception as ex:
                client.logger.exception(ex)

    async def process(self, global_event, event, channel) -> None:
        ignored_users = await get_first(await event.client.db.get_setting('TG_GLOBAL_EVENT_IGNORED_USERS'))
        if ignored_users and str(event.message.sender_id) in str(ignored_users['setting_value']).split(','):
            self.get_logger().debug('Skipped ignored global event user {}'.format(event.message.sender_id))
            return

        sender = await get_first(await event.client.db.getUserByTgChatId(event.message.sender_id))
        if sender is None:
            event.client.logger.info('Skipping event because sender user record not found: {}'.format(event.message.sender_id))
            return

        if await self.is_active_type(event, HalloweenMonsters.SilentPumpkin):
            await self.process_silent(global_event, event, channel, None, sender)
            return

        if not event.message.is_reply:
            return

        target_message = await event.message.get_reply_message()
        if target_message is None:
            return

        if target_message.sender_id != event.client.me.id:
            return

        if HalloweenConfig.is_event_reply(event.message) and HalloweenConfig.is_event_boss(target_message):
            await self.process_boss(global_event, event, channel, target_message, sender)
        elif HalloweenConfig.is_event_box_reply(event.message) and HalloweenConfig.is_event_box(target_message):
            await self.process_box(global_event, event, channel, target_message, sender)
        elif HalloweenConfig.is_event_reply(event.message) and HalloweenConfig.is_event_regular(target_message):
            await self.process_regular(global_event, event, channel, target_message, sender)
        elif HalloweenConfig.is_event_love_reply(event.message) and HalloweenConfig.is_event_love(target_message):
            await self.process_love(global_event, event, channel, target_message, sender)
        elif HalloweenConfig.is_event_number_reply(event.message) and HalloweenConfig.is_event_number(target_message):
            await self.process_number(global_event, event, channel, target_message, sender)
        elif HalloweenConfig.is_event_scary_reply(event.message) and HalloweenConfig.is_event_scary(target_message):
            await self.process_scary(global_event, event, channel, target_message, sender)
        else:
            return

    async def process_regular(self, event_data, event, channel, target_message, sender):
        event.client.logger.debug('routed to process_regular')
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
            destroyed = self.channels.hit_pumpkin(event.message.to_id.channel_id, target_message.id, sender['user_id'])
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

        try:
            await event.reply(text)
            await event.delete()
        except Exception as ex:
            self.get_logger().exception(ex)

        client.loop.create_task(self.channels.channels[event.message.to_id.channel_id].publish_pumpkin_amount_update(sender['user_id']))

    async def process_boss(self, event_data, event, channel, target_message, sender):
        if not await self.is_active(event, target_message):
            return

        try:
            self.channels.add_for_deletion(event.message.to_id.channel_id, event.message.id)
            if self.channels.hit_pumpkin(event.message.to_id.channel_id, target_message.id, sender['user_id']):
                await target_message.delete()
        except Exception as ex:
            self.get_logger().exception(ex)

    async def process_box(self, event_data, event, channel, target_message, sender):
        event.client.logger.debug('routed to process_box')
        if not await self.is_active(event, target_message):
            return

        try:
            if await event.client.db.is_cooldown_helloween_chestbox(sender['user_id']):
                try:
                    await event.delete()
                except:
                    pass
                return

            await event.client.db.set_helloween_chestbox_cooldown(sender['user_id'])
            self.channels.add_for_deletion(event.message.to_id.channel_id, event.message.id)
            if self.channels.hit_pumpkin(event.message.to_id.channel_id, target_message.id, sender['user_id']):
                await target_message.delete()
        except Exception as ex:
            self.get_logger().exception(ex)

    async def process_love(self, event_data, event, channel, target_message, sender):
        event.client.logger.info('routed to process_love')
        if not await self.is_active(event, target_message):
            return

        try:
            self.channels.add_for_deletion(event.message.to_id.channel_id, event.message.id)
            if self.channels.hit_pumpkin(event.message.to_id.channel_id, target_message.id, sender['user_id']):
                await target_message.delete()
        except Exception as ex:
            self.get_logger().exception(ex)

    async def process_scary(self, event_data, event, channel, target_message, sender):
        event.client.logger.info('routed to process_scary')
        if not await self.is_active(event, target_message):
            return

        try:
            self.channels.add_for_deletion(event.message.to_id.channel_id, event.message.id)
            if self.channels.hit_pumpkin(event.message.to_id.channel_id, target_message.id, sender['user_id']):
                await target_message.delete()
        except Exception as ex:
            self.get_logger().exception(ex)

    async def process_number(self, event_data, event, channel, target_message, sender):
        event.client.logger.info('routed to process_number')
        if not await self.is_active(event, target_message):
            return

        self.channels.add_for_deletion(event.message.to_id.channel_id, event.message.id)

        try:
            guess_number = int(event.message.text)
        except ValueError:
            return

        try:
            self.channels.add_for_deletion(event.message.to_id.channel_id, event.message.id)
            if self.channels.hit_pumpkin(event.message.to_id.channel_id, target_message.id, sender['user_id'], damage=guess_number):
                await target_message.delete()
        except Exception as ex:
            self.get_logger().exception(ex)

    async def process_silent(self, event_data, event, channel, target_message, sender):
        event.client.logger.info('routed to process_silent')

        try:
            target_id = self.channels.channels[event.message.to_id.channel_id].get_active_type_id(HalloweenMonsters.SilentPumpkin)
            self.channels.hit_pumpkin(event.message.to_id.channel_id, target_id, sender['user_id'])
        except Exception as ex:
            event.client.logger.exception(ex)

    async def is_active(self, event, message)->bool:
        try:
            if not self.channels.is_active(event.message.to_id.channel_id, message.id):
                try:
                    await event.delete()
                except:
                    pass

                event.client.logger.info('Skipping because message ID {} in channel {} is not active!'.format(message.id, event.message.to_id.channel_id))
                return False
        except:
            pass

        return True

    async def is_active_type(self, event, event_type)->bool:
        return self.channels.is_active_type(event.message.to_id.channel_id, event_type)
