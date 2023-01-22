import asyncio
from random import randint
from datetime import datetime, timedelta

from utils.constants import TG_TEST_GROUP_ID
from tgbot.events.global_events.GlobalEventProcessor import GlobalEventProcessor
from tgbot.events.global_events.winter.WinterType import WinterChannels, WinterConfig
from utils.array import get_first
from utils.formatting import format_html_user_mention


class WinterEventProcessor(GlobalEventProcessor):
    used_messages = {}

    def __init__(self, ):
        super().__init__()
        self.event_name = "winter"
        self.channels: WinterChannels = WinterChannels()
        self.get_logger().info("Created WinterEventProcessor")
        #self.register_task(self.item_spawner)
        self.register_task(self.snowball_generator)
        self.checking_snowman: bool = False


    async def snowball_generator(self, client):
        self.get_logger().info("Started winter snowball generator")

        details = await client.db.get_winter_generator_details()
        if details is None or details == {}:
            self.get_logger().info('Initiating new details config')
            details = {'next_run': None}

        async def calc_snowballs(calc_user, calc_channel)->int:
            sub_bonus = 0
            try:
                if calc_user['sub_type'] == '1000':
                    sub_bonus = 1
                elif calc_user['sub_type'] == '2000':
                    sub_bonus = 2
                elif calc_user['sub_type'] == '3000':
                    sub_bonus = 3

                subgift_history = await client.db.getSubgiftHistory(calc_channel['channel_id'], calc_user['user_id'])
                if subgift_history is not None:
                    for sub_hist in subgift_history:
                        if sub_hist['notice_type'] == 'subgift' and datetime.now() - timedelta(hours=48) < sub_hist['ts']:
                            sub_bonus += 2
                            break
            except Exception as ex:
                self.get_logger().exception(ex)

            return 1 + sub_bonus

        while True:
            if not await self.is_active_event(client):
                await asyncio.sleep(600 * self.speed)
                continue

            await self.update_channels(client)

            self.get_logger().info('Details: {}'.format(details))
            if details['next_run'] is not None:
                diff = details['next_run'] - datetime.utcnow()
                if details['next_run'] > datetime.utcnow() and diff.seconds > 0:
                    self.get_logger().info('Recovered after restart, sleeping for {} seconds'.format(diff))
                    await asyncio.sleep(diff.seconds * self.speed)
                self.get_logger().info('Starting snowball distribution (next_run was {})'.format(details['next_run']))

            if client.in_refresh:
                self.get_logger().info('Bot in refresh, delaying')
                await asyncio.sleep(120 * self.speed)
                continue

            event_channels = {}
            event_members = {}
            try:
                tg_channels = await client.db.get_auth_subchats()

                for tg_channel in tg_channels:
                    if tg_channel['tg_chat_id'] == 0:
                        continue

                    if tg_channel['global_events'] == 1:
                        event_channels[tg_channel['tg_chat_id']] = tg_channel
            except Exception as ex:
                self.get_logger().exception(ex)

            self.get_logger().info('Total event channels: {}'.format(len(event_channels.keys())))

            all_members = await client.db.getAllTgMembers()

            for member in all_members:
                if member['tg_chat_id'] not in event_channels:
                    continue

                user = await get_first(await client.db.getUserByTgChatId(member['tg_user_id']))
                if user is None:
                    continue

                member['user_id'] = user['user_id']
                member['snowballs'] = await calc_snowballs(member, event_channels[member['tg_chat_id']])

                if member['tg_user_id'] not in event_members or member['snowballs'] > event_members[member['tg_user_id']]['snowballs']:
                    event_members[member['tg_user_id']] = member

            total_snowballs = 0
            total_members = 0
            for member in event_members.keys():
                try:
                    total_members += 1
                    total_snowballs += event_members[member]['snowballs']

                    await client.db.add_currency_to_user(WinterConfig.currency_key, event_members[member]['user_id'], event_members[member]['snowballs'])
                    self.get_logger().info('Added {} snowballs to user {}'.format(event_members[member]['snowballs'], event_members[member]['user_id']))
                except Exception as ex:
                    self.get_logger().error('Failed to give {} snowballs to tg user ID {}'.format(event_members[member]['snowballs'], event_members[member]['tg_user_id']))
                    self.get_logger().exception(ex)

            await client.report_to_monitoring('Distributed {} snowballs to {} users in {} event chats.'.format(total_snowballs, total_members, len(event_channels.keys())))

            for tg_chat_id in event_channels.keys():
                try:
                    if tg_chat_id in self.channels.channels:
                        await self.channels.channels[tg_chat_id].send_random_snowing_sticker(client)
                        await asyncio.sleep(2)
                except Exception as ex:
                    self.get_logger().exception(ex)

            delay_mins = int(randint(180, 360) * self.speed)
            details['next_run'] = datetime.utcnow() + timedelta(minutes=delay_mins)
            await client.db.set_winter_generator_details(details)
            self.get_logger().info('End of snow distribution, (next_run = {}, delay = {})'.format(details['next_run'], delay_mins))
            await asyncio.sleep(delay_mins*60 * self.speed)

    async def item_spawner(self, client):
        self.get_logger().info("Started winter item spawner")

        delay = 60
        while True:
            await asyncio.sleep(delay * self.speed)

            try:
                if not await self.is_active_event(client):
                    delay = 600
                    continue

                delay = 60
                await self.update_channels(client)

                for key in self.channels.channels.keys():
                    if int(key) != TG_TEST_GROUP_ID:
                        continue

                    count = int(await client.get_group_member_count(int(key)))
                    if self.channels.channels[key].can_start_snowing(count):
                        await self.channels.channels[key].spawn_snowing(client, member_count=count)
                        await asyncio.sleep(randint(2, 15) * self.speed)
            except Exception as ex:
                client.logger.exception(ex)

    async def process(self, global_event, event, channel):
        # if channel['tg_chat_id'] != TG_TEST_GROUP_ID:
        #     return

        if not event.message.is_reply:
            return

        target_message = await event.message.get_reply_message()
        if target_message is None:
            return

        # skip interactions with self
        if target_message.sender_id == event.message.sender_id:
            return

        sender = await get_first(await event.client.db.getUserByTgChatId(event.message.sender_id))
        if sender is None:
            self.get_logger().info('Skipping event because sender user record not found: {}'.format(event.message.sender_id))
            return

        bot_iniator = target_message.sender_id == event.client.me.id

        if WinterConfig.is_snowball(event.message) and WinterConfig.is_snowball(target_message):
            await self.process_snowball_fight(global_event, event, channel, target_message, sender)
        elif bot_iniator and WinterConfig.starts_with_snowball(event.message) and WinterConfig.is_storage_sticker(target_message):
            await self.process_snowball_storing(global_event, event, channel, target_message, sender)
        else:
            #event.client.logger.info('Unknown event from message {} to message {} in channel {}'.format(event.message.id, target_message.id, channel))
            return

    async def process_snowing_message(self, event_data, event, channel, target_message, sender):
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
        self.channels.add_for_deletion(event.message.to_id.channel_id, event.message.id)
        self.channels.take_snowballs(event.message.to_id.channel_id, target_message.id, sender['user_id'])

    async def process_snowball_storing(self, event_data, event, channel, target_message, sender):
        client = event.client

        try:
            encoded = event.message.text.encode()
            for emote in WinterConfig.snowballs_encoded:
                encoded = encoded.replace(emote, b'')
            transfer_amount = encoded.decode().strip()
            if transfer_amount == '':
                transfer_amount = 1
            else:
                transfer_amount = int(transfer_amount)
        except Exception as ex:
            self.get_logger().info(ex)
            transfer_amount = 1

        if transfer_amount < 1:
            return

        sender = await get_first(await client.db.getUserByTgChatId(event.message.sender_id))
        if sender is None:
            self.get_logger().info('Skipping event because sender user record not found: {}'.format(event.message.sender_id))
            return

        sender_currency = await get_first(await client.db.get_user_currency_amount(WinterConfig.currency_key, sender['user_id']))
        if sender_currency is None or 'amount' not in sender_currency or sender_currency['amount'] < transfer_amount:
            await event.reply(client.translator.getLangTranslation(channel['bot_lang'], 'CMD_CHAT_INVENTORY_ADD_INSUFFICIENT'))
            self.get_logger().info('Skipping event because sender user {} dont have currency: {}'.format(sender['user_id'], sender_currency))
            return

        await client.db.add_currency_to_user(WinterConfig.currency_key, sender['user_id'], -1 * transfer_amount)
        await client.db.add_currency_to_channel(WinterConfig.currency_key, channel['channel_id'], transfer_amount)

        try:
            await event.delete()
        except Exception as ex:
            client.logger.exception(ex)

        item_text = client.translator.getLangTranslation(channel['bot_lang'], "INVENTORY_ITEM_" + WinterConfig.currency_key.upper())
        sender_entity = await client.get_entity(event.message.sender_id)
        sender_label = await format_html_user_mention(sender_entity)
        text = client.translator.getLangTranslation(channel['bot_lang'], 'CMD_CHAT_INVENTORY_ADD_SUCCESS').format(amount=transfer_amount, item=item_text, user=sender_label)
        await event.reply(text)
        client.loop.create_task(self.check_for_snowman(client, channel))

    async def check_for_snowman(self, client, channel):
        checks = 0
        while self.checking_snowman:
            await asyncio.sleep(2)
            checks += 1

            if checks >= 20:
                return

        self.checking_snowman = True
        convert_ration = 100  # How many snowballs needed for snowman
        try:
            datas = await client.db.getTgChatCurrency(channel['channel_id'])
            for data in datas:
                if data['currency_key'] == WinterConfig.currency_key and data['amt'] >= convert_ration:
                    current_snowballs = int(data['amt'])
                    new_snowmans = int((current_snowballs - (current_snowballs % convert_ration)) / convert_ration)
                    if new_snowmans > 0:
                        await client.db.add_currency_to_channel(WinterConfig.currency_key, channel['channel_id'], -1 * new_snowmans * convert_ration)
                        await client.db.add_currency_to_channel('snowman', channel['channel_id'], new_snowmans)
                        text = client.translator.getLangTranslation(channel['bot_lang'], "GLOBAL_EVENT_WINTER_CREATED_SNOWMAN").format(amount=new_snowmans)
                        await client.send_message(channel['tg_chat_id'], text)
                        return


        except Exception as ex:
            self.get_logger().exception(ex)
        finally:
            self.checking_snowman = False

    async def process_snowball_fight(self, event_data, event, channel, target_message, sender):
        client = event.client

        if channel['tg_chat_id'] not in WinterEventProcessor.used_messages:
            WinterEventProcessor.used_messages[channel['tg_chat_id']] = []

        target_user = await get_first(await client.db.getUserByTgChatId(target_message.sender_id))
        if target_user is None:
            self.get_logger().info('Skipping event because target user record not found: {}'.format(target_message.sender_id))
            return

        sender = await get_first(await client.db.getUserByTgChatId(event.message.sender_id))
        if sender is None:
            self.get_logger().info('Skipping event because sender user record not found: {}'.format(event.message.sender_id))
            return

        sender_entity = await client.get_entity(event.message.sender_id)
        target_entity = await client.get_entity(target_message.sender_id)

        sender_label = await format_html_user_mention(sender_entity)
        target_label = await format_html_user_mention(target_entity)

        target_currency = await get_first(await client.db.get_user_currency_amount(WinterConfig.currency_key, target_user['user_id']))
        if target_currency is None or not target_currency['amount']:
            await event.reply(client.translator.getLangTranslation(channel['bot_lang'], 'GLOBAL_EVENT_WINTER_FIGHT_MISSING').format(user=target_label))
            self.get_logger().info('Skipping event because target user {} dont have currency: {}'.format(target_user['user_id'], target_currency))
            return

        sender_currency = await get_first(await client.db.get_user_currency_amount(WinterConfig.currency_key, sender['user_id']))
        if sender_currency is None or not sender_currency['amount']:
            await event.reply(client.translator.getLangTranslation(channel['bot_lang'], 'GLOBAL_EVENT_WINTER_FIGHT_MISSING').format(user=sender_label))
            self.get_logger().info('Skipping event because sender user {} dont have currency: {}'.format(sender['user_id'], sender_currency))
            return

        if event.message.id in WinterEventProcessor.used_messages[channel['tg_chat_id']] or target_message.id in WinterEventProcessor.used_messages[channel['tg_chat_id']]:
            self.get_logger().info('Skipping because used on existing event message: {}, sender {} target {}'.format(WinterEventProcessor.used_messages[channel['tg_chat_id']], event.message.id, target_message.id))
            return

        WinterEventProcessor.used_messages[channel['tg_chat_id']].append(event.message.id)
        WinterEventProcessor.used_messages[channel['tg_chat_id']].append(target_message.id)
        try:
            await event.delete()
            await target_message.delete()
        except Exception as ex:
            self.get_logger().exception(ex)



        roll = randint(1, 1000)
        text = 'Potato situation'
        if roll < 495:
            text = client.translator.getLangTranslation(channel['bot_lang'], 'GLOBAL_EVENT_WINTER_FIGHT_SINGLE_WIN').format(winner=target_label)
            await client.db.add_currency_to_user(WinterConfig.currency_key, target_user['user_id'], 1)
            await client.db.add_currency_to_user('snowball_wins', target_user['user_id'], 1)
            await client.db.add_currency_to_user(WinterConfig.currency_key, sender['user_id'], -1)
        elif roll < 989:
            text = client.translator.getLangTranslation(channel['bot_lang'], 'GLOBAL_EVENT_WINTER_FIGHT_SINGLE_WIN').format(winner=sender_label)
            await client.db.add_currency_to_user(WinterConfig.currency_key, target_user['user_id'], -1)
            await client.db.add_currency_to_user(WinterConfig.currency_key, sender['user_id'], 1)
            await client.db.add_currency_to_user('snowball_wins', sender['user_id'], 1)
        elif roll < 995:
            text = client.translator.getLangTranslation(channel['bot_lang'], 'GLOBAL_EVENT_WINTER_FIGHT_DOUBLE_LOSS').format(target=target_label, sender=sender_label)
            await client.db.add_currency_to_user(WinterConfig.currency_key, target_user['user_id'], -1)
            await client.db.add_currency_to_user(WinterConfig.currency_key, sender['user_id'], -1)
        elif roll < 1001:
            text = client.translator.getLangTranslation(channel['bot_lang'], 'GLOBAL_EVENT_WINTER_FIGHT_DOUBLE_WIN').format(winner=target_label, sender=sender_label)
            await client.db.add_currency_to_user(WinterConfig.currency_key, target_user['user_id'], 1)
            await client.db.add_currency_to_user(WinterConfig.currency_key, sender['user_id'], 1)
            await client.db.add_currency_to_user('snowball_wins', target_user['user_id'], 1)
            await client.db.add_currency_to_user('snowball_wins', sender['user_id'], 1)

        await client.db.add_currency_to_user('snowball_fights', target_user['user_id'], 1)
        await client.db.add_currency_to_user('snowball_fights', sender['user_id'], 1)

        response = await client.send_message(channel['tg_chat_id'], text)
        await asyncio.sleep(120 * self.speed)
        await response.delete()
