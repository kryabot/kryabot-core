import asyncio
from datetime import datetime, timedelta
from typing import Dict
from random import randint

from telethon.tl.types import DocumentAttributeSticker

from tgbot.events.global_events.GlobalEventProcessor import EventChannels, EventChannel
from tgbot.events.global_events.winter import WinterItem
from utils.array import get_first


class WinterChannels(EventChannels):
    def __init__(self):
        super().__init__(WinterChannel)

    def is_active(self, channel_id, message_id)->bool:
        return self.channels[channel_id].is_active(message_id)

    def take_snowballs(self, channel_id: int, message_id: int, user_id: int)->bool:
        channel: WinterChannel = self.channels[channel_id]
        return channel.interact(message_id, user_id)

    def is_test(self, channel_id: int, message_id: int)->bool:
        channel: WinterChannel = self.channels[channel_id]
        return channel.is_test(message_id)

    def add_for_deletion(self, channel_id: int, message_id: int):
        channel: WinterChannel = self.channels[channel_id]
        channel.delete_messages.append(message_id)


class WinterChannel(EventChannel):
    def __init__(self, channel_id, lang):
        super().__init__(channel_id, lang)
        self.next_snowing: datetime = None
        self.items: Dict[int, WinterItem.WinterItem] = {}
        self.delete_messages: [int] = []
        self.client = None

    def delete(self, msg_id: int):
        self.items[int(msg_id)] = None

    def disable(self, msg_id: int):
        self.items[int(msg_id)].active = False

    def exists(self, message_id: int)->bool:
        return message_id in self.items and self.items[message_id].active

    def is_test(self, message_id: int)->bool:
        return self.items[message_id].test

    def already_interacted(self, msg_id: int, user_id: int)->bool:
        return self.items[msg_id].already_interacted(user_id)

    def interact(self, msg_id: int, user_id: int)->bool:
        return self.items[msg_id].interact(user_id)

    def save(self, item: WinterItem.WinterItem)->None:
        self.items[int(item.msg_id)] = item

    def get_participants(self, msg_id: int):
        return self.items[int(msg_id)].participants

    def calc_next_snowing(self, member_count: int):
        # TODO: calc logic
        self.next_snowing = datetime.utcnow() + timedelta(minutes=60)
        self.get_logger().info('Updated next snowing spawn to {} for channel {} (now = {})'.format(self.next_snowing, self.channel_id, datetime.utcnow()))

    def can_start_snowing(self, member_count: int)->bool:
        if self.next_snowing is None:
            self.calc_next_snowing(member_count)

        return self.can_spawn() and self.next_snowing < datetime.utcnow()

    async def spawn_snowing(self, client, member_count: int, test: bool=False)->None:
        self.last_spawn = datetime.utcnow()
        self.client = client
        self.calc_next_snowing(member_count)

        msg = await self.send_random_snowing_sticker(client)
        self.get_logger().info("Started snowing ID {} in channel {}".format(msg.id, self.channel_id))

        item = WinterItem.Snowing(msg_id=msg.id, test=test)
        self.save(item)

        client.loop.create_task(self.updater_snowing(client, msg))

    async def send_random_snowing_sticker(self, client):
        random_sets = []
        random_sets.append({'name': 'SweetySanta', 'emote': '❄'})
        random_sets.append({'name': 'ChristmasDogs', 'emote': '🥶'})
        random_sets.append({'name': 'SnowBabbit', 'emote': '❄'})
        random_sets.append({'name': 'MuffinMan', 'emote': '❄'})
        random_sets.append({'name': 'LilCifer', 'emote': '🥶'})
        random_sets.append({'name': 'UtyaDuck', 'emote': '❄'})
        random_sets.append({'name': 'FishPrometheus', 'emote': '❄'})

        val = randint(0, len(random_sets) - 1)
        random_set = random_sets[val]

        sticker_set = await client.get_sticker_set(random_set['name'])
        for sticker in sticker_set.packs:
            if sticker.emoticon == random_set['emote']:
                for pack in sticker_set.documents:
                    if sticker.documents[0] == pack.id:
                        try:
                            sticker_message = await client.send_file(self.channel_id, pack)
                            sticker_id, sticker_emote = WinterConfig.get_sticker_id_and_emote(message=sticker_message)
                            if sticker_emote is not None and sticker_emote not in WinterConfig.snowing_emotes_for_sticker:
                                self.get_logger().info('Adding emote {} to list'.format(sticker_emote))
                                WinterConfig.snowing_emotes_for_sticker.append(sticker_emote)
                            self.get_logger().info('End of send_random_snowing_sticker')
                            return sticker_message
                        except Exception as ex:
                            self.get_logger().exception(ex)

    async def updater_snowing(self, client, event_message):
        client.logger.info('Starting updater_snowing for message {} in channel {}'.format(event_message.id, self.channel_id))
        self.client = client
        default_text = client.translator.getLangTranslation(self.lang, 'EVENT_SNOWING_INFO')
        last_text = ""
        info_message = None
        start_ts = datetime.utcnow()
        alive_seconds = 60

        while True:
            await asyncio.sleep(1)

            if start_ts + timedelta(seconds=alive_seconds) < datetime.utcnow():
                self.disable(event_message.id)

            participants = self.get_participants(event_message.id)
            if self.exists(event_message.id):
                new_text = default_text.format(emotes=' '.join(WinterConfig.snowing_emotes), total=len(participants.keys()))
                if new_text == last_text:
                    continue
                else:
                    try:
                        last_text = new_text
                        if info_message is None:
                            info_message = await client.send_message(self.channel_id, new_text, reply_to=event_message.id)
                        else:
                            await info_message.edit(new_text)
                    except Exception as ex:
                        self.get_logger().exception(ex)
            else:
                try:
                    self.delete_messages.append(info_message.id)
                    self.delete_messages.append(event_message.id)
                    self.get_logger().info("Deleting messages: {}".format(self.delete_messages))
                    result = await client.delete_messages(entity=self.channel_id, message_ids=self.delete_messages)
                except Exception as ex:
                    self.get_logger().exception(ex)

                self.delete_messages = []
                #if participants is not None and not self.is_test(event_message.id):
                if participants is not None:
                    client.loop.create_task(self.distribute_snowballs(participants))

                # If its not active anymore then post results
                final_text = client.translator.getLangTranslation(self.lang, 'EVENT_SNOWING_ENDS').format(total=len(participants.keys()))
                try:
                    await client.send_message(self.channel_id, final_text)
                except Exception as ex:
                    self.get_logger().exception(ex)

                break

            await asyncio.sleep(3)

    async def distribute_snowballs(self, participants, sub_only=False, sub_extra=2):
        channel = await get_first(await self.client.db.getSubchatWithAuth(self.channel_id))
        for user_id in participants.keys():
            try:
                user = await get_first(await self.client.db.getUserByTgChatId(user_id))
                if sub_only or sub_extra > 0:
                    try:
                        is_sub = await self.client.api.is_sub_v2(channel, user, self.client.db)
                    except Exception as ex:
                        is_sub = False
                else:
                    is_sub = False

                if sub_only and not is_sub:
                    continue

                points = 2
                if is_sub:
                    points += sub_extra

                await self.client.db.add_currency_to_user(WinterConfig.currency_key, user_id, points)
                # TODO: publishing
                # client.loop.create_task(self.publish_pumpkin_amount_update(user_id))
            except Exception as ue:
                self.get_logger().error('Failed to add result to user {} in channel {}'.format(user_id, self.channel_id))
                self.get_logger().exception(ue)

class WinterConfig:
    snowing_message = "TODO: snowing sticker"
    snowing_emotes = ['❄️', '❄']
    currency_key = 'snowball'
    snowball_emote = '⚪️'
    snowball_emotes = ['⚪️', '⚪️', '⚪']
    snowballs_encoded = [b'\xe2\x9a\xaa\xef\xb8\x8f', b'\xe2\x9a\xaa']

    snowing_emotes_for_sticker = ['❄', '🥶']

    @staticmethod
    def is_snowing_message(message)->bool:
        return message.text == WinterConfig.snowing_message

    @staticmethod
    def is_snowing_reply(message)->bool:
        return message.text in WinterConfig.snowing_emotes

    @staticmethod
    def is_snowing_sticker_message(message)->bool:
        doc_ids = [1068685509326275489, 1048388279864393870, 1269403972611866840, 1451390786439479367, 328260442013040879, 773947703670341897, 1137162165791228038]
        ids = [1068685509326274587, 1048388279864393735, 1269403972611866630, 1451390786439479299, 328260442013040643, 773947703670341644, 1137162165791227907]

        if message.media and message.document:
            return message.media.document.id in doc_ids

        sticker_id, sticker_emote = WinterConfig.get_sticker_id_and_emote(message)
        print(sticker_id, sticker_emote)
        return sticker_id in ids and sticker_emote in WinterConfig.snowing_emotes_for_sticker

    @staticmethod
    def get_sticker_id_and_emote(message):
        if not message.sticker:
            return None, None

        for attr in message.media.document.attributes:
            if isinstance(attr, DocumentAttributeSticker):
                return attr.stickerset.id, attr.alt

        return None, None

    @staticmethod
    def is_snowball(message)->bool:
        return message.text.encode() in WinterConfig.snowballs_encoded

    @staticmethod
    def starts_with_snowball(message)->bool:
        if not message.text:
            return False

        for emote in WinterConfig.snowballs_encoded:
            if message.text.encode().startswith(emote):
                return True

        return False

    @staticmethod
    def is_storage_sticker(message)->bool:
        return message.media and message.document and message.document.id == 1299861509853151283
