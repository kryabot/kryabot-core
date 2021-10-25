import asyncio
import logging
import math
from datetime import datetime, timedelta
from typing import Dict, List
from random import randint

from telethon.tl.types import DocumentAttributeSticker

from tgbot.events.global_events.GlobalEventProcessor import EventChannels, EventChannel
from tgbot.events.global_events.halloween import HalloweenMonsters
from utils import redis_key
from utils.array import get_first
from utils.formatting import format_html_user_mention

logger: logging = logging.getLogger('krya.tg')


class HalloweenChannels(EventChannels):
    def __init__(self):
        super().__init__(HalloweenChannel)

    def is_active(self, channel_id, message_id)->bool:
        return self.channels[channel_id].is_active(message_id)

    def is_active_type(self, channel_id, check_type)->bool:
        if channel_id in self.channels:
            logger.debug('Active: {} {} {}'.format(channel_id, check_type, self.channels[channel_id].is_active_type(check_type)))
            return self.channels[channel_id].is_active_type(check_type)
        return False

    def hit_pumpkin(self, channel_id: int, message_id: int, user_id: int, damage: int = 1)->bool:
        channel: HalloweenChannel = self.channels[channel_id]
        logger.debug('hitting {} from {}'.format(message_id, user_id))
        return channel.hit_pumpkin(message_id, user_id, custom_damage=damage)

    def add_for_deletion(self, channel_id: int, message_id: int):
        channel: HalloweenChannel = self.channels[channel_id]
        channel.delete_messages.append(message_id)

    def remove_pumpkin(self, channel_id: int, message_id: int):
        channel: HalloweenChannel = self.channels[channel_id]
        channel.delete(message_id)

    def is_test(self, channel_id: int, message_id: int)->bool:
        channel: HalloweenChannel = self.channels[channel_id]
        return channel.is_test(message_id)


class HalloweenChannel(EventChannel):
    def __init__(self, channel_id, lang):
        super().__init__(channel_id, lang)
        self.pumpkins: Dict[int, HalloweenMonsters.Monster] = {}
        self.last_regular: datetime = datetime.utcnow()
        self.last_boss: datetime = datetime.utcnow()
        self.last_box: datetime = datetime.utcnow()
        self.last_love: datetime = datetime.utcnow()
        self.last_number: datetime = datetime.utcnow()
        self.last_silent: datetime = datetime.utcnow()
        self.last_scary: datetime = datetime.utcnow()
        self.last_greedy: datetime = datetime.utcnow()
        self.delete_messages: List[int] = []
        self.client = None
        self.next_boss: datetime = None
        self.next_box: datetime = None
        self.next_love: datetime = None
        self.next_number: datetime = None
        self.next_silent: datetime = None
        self.next_scary: datetime = None
        self.next_greedy: datetime = None
        self.channel_size: int = 1
        self.last_spawn: datetime = datetime.utcnow()

    def is_test(self, msg_id: int)->bool:
        if not int(msg_id) in self.pumpkins:
            return False

        return self.pumpkins[int(msg_id)].test

    def is_active(self, msg_id: int)->bool:
        if not int(msg_id) in self.pumpkins:
            return False

        return self.pumpkins[int(msg_id)].is_active()

    def is_active_type(self, check_type)->bool:
        for item_id in self.pumpkins.keys():
            if isinstance(self.pumpkins[item_id], check_type) and self.pumpkins[item_id].is_active():
                return True

        return False

    def get_active_type_id(self, check_type):
        for item_id in self.pumpkins.keys():
            if isinstance(self.pumpkins[item_id], check_type) and self.pumpkins[item_id].is_active():
                return int(item_id)

        return None

    def has_active_pumpkin(self)->bool:
        for key in self.pumpkins.keys():
            if self.pumpkins[key] is not None and self.pumpkins[key].active:
                return True

        return False

    def hit_pumpkin(self, msg_id: int, user_id: int, custom_damage: int=1)->bool:
        if msg_id not in self.pumpkins:
            return False

        logger.info("Pumpkin {} was hit after {} seconds by {}".format(msg_id, (datetime.utcnow() - self.pumpkins[int(msg_id)].created).seconds, user_id))
        monster: HalloweenMonsters.Monster = self.pumpkins[msg_id]

        if monster.is_boss():
            dmg: int = HalloweenConfig.roll_incremental(2, 5)
        else:
            dmg = custom_damage

        died: bool = monster.hit(user_id, dmg)

        if died and monster.is_boss():
            self.calc_next_boss_spawn()

        return died

    def calc_next_greedy_spawn(self):
        ratio = HalloweenConfig.calc(self.channel_size, limit=200)
        min_time = int(ratio * 2)
        max_time = int(ratio * 3)
        delay = randint(min_time, max_time)
        self.next_greedy = datetime.utcnow() + timedelta(minutes=delay)
        logger.info('Updated next greedy spawn to {} for channel {} (now = {})'.format(self.next_greedy, self.channel_id, datetime.utcnow()))

    def calc_next_love_spawn(self):
        ratio = HalloweenConfig.calc(self.channel_size, limit=200)
        min_time = int(ratio * 1.5)
        max_time = int(ratio * 2)
        delay = randint(min_time, max_time)
        self.next_love = datetime.utcnow() + timedelta(minutes=delay)
        logger.info('Updated next love spawn to {} for channel {} (now = {})'.format(self.next_love, self.channel_id, datetime.utcnow()))

    def calc_next_scary_spawn(self):
        ratio = HalloweenConfig.calc(self.channel_size, limit=200)
        min_time = int(ratio * 1.5)
        max_time = int(ratio * 2)
        delay = randint(min_time, max_time)
        self.next_scary = datetime.utcnow() + timedelta(minutes=delay)
        logger.info('Updated next love spawn to {} for channel {} (now = {})'.format(self.next_scary, self.channel_id, datetime.utcnow()))

    def calc_next_boss_spawn(self):
        ratio = HalloweenConfig.calc(self.channel_size)
        min_time = min(int(ratio), 120)
        max_time = max(int(ratio), 180)
        delay = randint(min_time, max_time)
        self.next_boss = datetime.utcnow() + timedelta(minutes=delay)
        logger.info('Updated next boss spawn to {} for channel {} (now = {})'.format(self.next_boss, self.channel_id, datetime.utcnow()))

    def calc_next_number_spawn(self):
        ratio = HalloweenConfig.calc(self.channel_size)
        min_time = min(int(ratio), 120)
        max_time = max(int(ratio), 180)
        delay = randint(min_time, max_time)
        self.next_number = datetime.utcnow() + timedelta(minutes=delay)
        logger.info('Updated next number spawn to {} for channel {} (now = {})'.format(self.next_number, self.channel_id, datetime.utcnow()))

    def calc_next_silent_spawn(self):
        ratio = HalloweenConfig.calc(self.channel_size)
        min_time = min(int(ratio), 120)
        max_time = max(int(ratio), 250)
        delay = randint(min_time, max_time)
        self.next_silent = datetime.utcnow() + timedelta(minutes=delay)
        logger.info('Updated next number spawn to {} for channel {} (now = {})'.format(self.next_silent, self.channel_id, datetime.utcnow()))

    def calc_next_box_spawn(self):
        ratio = HalloweenConfig.calc(self.channel_size, limit=300)
        min_time = int(ratio * 6)
        max_time = int(ratio * 9)
        delay = randint(min_time, max_time)
        self.next_box = datetime.utcnow() + timedelta(minutes=delay)
        logger.info('Updated next box spawn to {} for channel {} (now = {})'.format(self.next_box, self.channel_id, datetime.utcnow()))

    def can_spawn_boss(self, channel_size: int) -> bool:
        self.channel_size = channel_size
        if channel_size < 20:
            return False

        if self.has_active_pumpkin() or not self.spawn_delay_passed():
            return False

        if self.next_boss is None:
            self.calc_next_boss_spawn()

        return self.next_boss < datetime.utcnow()

    def can_spawn_regular(self, channel_size: int)->bool:
        self.channel_size = channel_size
        if self.has_active_pumpkin() or not self.spawn_delay_passed():
            return False

        ratio = HalloweenConfig.calc(channel_size)
        min_time = max(int(ratio / 5), 10)
        max_time = max(int(ratio / 4), 30)
        delay = randint(min_time, max_time)
        if self.last_regular + timedelta(minutes=delay) < datetime.utcnow():
            return True

        return False

    def can_spawn_box(self, channel_size: int)->bool:
        self.channel_size = channel_size
        if self.has_active_pumpkin() or not self.spawn_delay_passed():
            return False

        if self.next_box is None:
            self.calc_next_box_spawn()

        return self.next_box < datetime.utcnow()

    def can_spawn_love(self, channel_size: int)->bool:
        self.channel_size = channel_size
        if self.has_active_pumpkin() or not self.spawn_delay_passed():
            return False

        if self.next_love is None:
            self.calc_next_love_spawn()

        return self.next_love < datetime.utcnow()

    def can_spawn_greedy(self, channel_size: int)->bool:
        self.channel_size = channel_size
        if self.has_active_pumpkin() or not self.spawn_delay_passed():
            return False

        if self.next_greedy is None:
            self.calc_next_greedy_spawn()

        return self.next_greedy < datetime.utcnow()

    def can_spawn_scary(self, channel_size: int)->bool:
        self.channel_size = channel_size
        if self.has_active_pumpkin() or not self.spawn_delay_passed():
            return False

        if self.next_scary is None:
            self.calc_next_scary_spawn()

        return self.next_scary < datetime.utcnow()

    def can_spawn_number(self, channel_size: int)->bool:
        self.channel_size = channel_size
        if self.has_active_pumpkin() or not self.spawn_delay_passed():
            return False

        if self.next_number is None:
            self.calc_next_number_spawn()

        return self.next_number < datetime.utcnow()

    def can_spawn_silent(self, channel_size: int)->bool:
        self.channel_size = channel_size
        if self.has_active_pumpkin() or not self.spawn_delay_passed():
            return False

        if self.next_silent is None:
            self.calc_next_silent_spawn()

        return self.next_silent < datetime.utcnow()

    def save(self, monster: HalloweenMonsters.Monster):
        self.pumpkins[int(monster.msg_id)] = monster

    def delete(self, msg_id: int):
        self.pumpkins[int(msg_id)] = None

    def spawn_delay_passed(self)->bool:
        return self.last_spawn + timedelta(minutes=15) < datetime.utcnow()

    async def spawn_regular(self, client, size: int, test: bool=False):
        self.client = client
        self.last_regular = datetime.utcnow()
        self.last_spawn = datetime.utcnow()

        msg = await client.send_message(self.channel_id, HalloweenConfig.pumpkin_message)
        client.logger.info("Spawned regular pumpkin ID {} in channel {}".format(msg.id, self.channel_id))

        monster = HalloweenMonsters.RegularPumpkin(msg_id=msg.id, test=test)
        self.save(monster)

    async def spawn_greedy_pumpkin(self, client, size: int, test: bool=False):
        self.client = client
        self.last_spawn = datetime.utcnow()
        self.last_love = datetime.utcnow()
        msg = await self.send_halloween_cube_sticker(client, self.channel_id, HalloweenConfig.pumpkin_greedy)
        client.logger.info("Spawned greedy pumpkin ID {} in channel {}".format(msg.id, self.channel_id))
        monster = HalloweenMonsters.GreedyPumpkin(msg_id=msg.id, hp=1, test=test)
        self.save(monster)
        client.loop.create_task(self.pumpkin_greedy_info_updater(client, msg))
        self.calc_next_greedy_spawn()

    async def spawn_love_pumpkin(self, client, size: int, test: bool=False):
        self.client = client
        self.last_spawn = datetime.utcnow()
        self.last_love = datetime.utcnow()
        msg = await self.send_halloween_sticker(client, self.channel_id, HalloweenConfig.pumpkin_heart)
        client.logger.info("Spawned love pumpkin ID {} in channel {}".format(msg.id, self.channel_id))
        monster = HalloweenMonsters.LovePumpkin(msg_id=msg.id, hp=10000, test=test)
        self.save(monster)
        client.loop.create_task(self.pumpkin_love_info_updater(client, msg))
        self.calc_next_love_spawn()

    async def spawn_scary(self, client, size: int, test: bool=False):
        self.client = client
        self.last_spawn = datetime.utcnow()
        self.last_scary = datetime.utcnow()
        msg = await self.send_halloween_sticker(client, self.channel_id, HalloweenConfig.pumpkin_scary)
        client.logger.info("Spawned scary pumpkin ID {} in channel {}".format(msg.id, self.channel_id))
        monster = HalloweenMonsters.ScaryPumpkin(msg_id=msg.id, hp=10000, test=test)
        self.save(monster)
        client.loop.create_task(self.pumpkin_scary_info_updater(client, msg))
        self.calc_next_scary_spawn()

    async def spawn_boss(self, client, size: int, test: bool=False):
        self.client = client
        self.last_boss = datetime.utcnow()
        self.last_spawn = datetime.utcnow()

        msg = await self.send_halloween_sticker(client, self.channel_id, HalloweenConfig.pumpkin_boss)
        client.logger.info("Spawned boss pumpkin ID {} in channel {}".format(msg.id, self.channel_id))

        monster = HalloweenMonsters.BossPumpkin(msg_id=msg.id, hp=HalloweenConfig.calc_boss_hp(size), test=test)
        self.save(monster)
        client.loop.create_task(self.pumpkin_boss_info_updater(client, msg))

    async def spawn_number(self, client, size: int, test: bool=False):
        self.client = client
        self.last_number = datetime.utcnow()
        self.last_spawn = datetime.utcnow()

        msg = await self.send_halloween_sticker(client, self.channel_id, HalloweenConfig.pumpkin_number)
        client.logger.info("Spawned number pumpkin ID {} in channel {}".format(msg.id, self.channel_id))

        monster = HalloweenMonsters.NumberPumpkin(msg_id=msg.id, hp=0, test=test)
        self.save(monster)
        client.loop.create_task(self.pumpkin_number_info_updater(client, msg))
        self.calc_next_number_spawn()

    async def spawn_silent(self, client, size: int, test: bool=False):
        self.client = client
        self.last_silent = datetime.utcnow()
        self.last_spawn = datetime.utcnow()

        msg = await self.send_halloween_sticker(client, self.channel_id, HalloweenConfig.pumpkin_silent)
        client.logger.info("Spawned silent pumpkin ID {} in channel {}".format(msg.id, self.channel_id))

        monster = HalloweenMonsters.SilentPumpkin(msg_id=msg.id, hp=1, test=test)
        self.save(monster)
        client.loop.create_task(self.pumpkin_silent_info_updater(client, msg))
        self.calc_next_silent_spawn()

    async def spawn_box(self, client, size: int, test: bool=False):
        self.client = client
        self.last_box = datetime.utcnow()
        self.last_spawn = datetime.utcnow()

        msg = await self.send_kryabot_events_sticker(client, self.channel_id, HalloweenConfig.chestbox)
        client.logger.info("Spawned box pumpkin ID {} in channel {}".format(msg.id, self.channel_id))

        monster = HalloweenMonsters.ChestBox(msg_id=msg.id, hp=1, test=test)
        self.save(monster)
        client.loop.create_task(self.pumpkin_chestbox_info_updater(client, msg))
        self.calc_next_box_spawn()

    async def send_sticker(self, client, channel_id, sticker_pack_name, emote):
        stickers = await client.get_sticker_set(sticker_pack_name)
        for sticker in stickers.packs:
            if sticker.emoticon == emote:
                for pack in stickers.documents:
                    if sticker.documents[0] == pack.id:
                        return await client.send_file(channel_id, pack)

    async def send_halloween_sticker(self, client, channel_id, emote):
        return await self.send_sticker(client, channel_id, 'Halloweenkin', emote)

    async def send_halloween_cube_sticker(self, client, channel_id, emote):
        return await self.send_sticker(client, channel_id, 'PumpkinCube', emote)

    async def send_kryabot_events_sticker(self, client, channel_id, emote):
        return await self.send_sticker(client, channel_id, 'KryaBotEvents', emote)

    def get_attackers(self, msg_id: int):
        if msg_id not in self.pumpkins:
            return None

        return self.pumpkins[msg_id].damagers

    async def pumpkin_silent_info_updater(self, client, event_message):
        self.client = client
        start_ts = datetime.utcnow()
        client.logger.info('Starting pumpkin_silent_info_updater for message {} in channel {}'.format(event_message.id, self.channel_id))
        default_text = '🎬 ' + client.translator.getLangTranslation(self.lang, 'EVENT_PUMPKIN_SILENT_INFO')
        info_message = None
        alive_seconds = randint(50, 80)
        finish_ts = start_ts + timedelta(seconds=alive_seconds)
        reward = randint(1, 2)

        while True:
            await asyncio.sleep(1)

            attackers = self.get_attackers(event_message.id)
            if finish_ts < datetime.utcnow() or attackers:
                self.calc_next_silent_spawn()
                self.pumpkins[event_message.id].kill()

            if self.is_active(event_message.id):
                remaining_seconds = (finish_ts - datetime.utcnow()).seconds
                remaining_seconds = max(remaining_seconds, 0)
                info_text = default_text.format(seconds=remaining_seconds)
                try:
                    if not info_message:
                        info_message = await client.send_message(self.channel_id, info_text, reply_to=event_message.id)
                    else:
                        if remaining_seconds > 0:
                            await info_message.edit(info_text)
                except Exception as ex:
                    logger.exception(ex)
            else:
                try:
                    if info_message:
                        self.delete_messages.append(info_message.id)
                    self.delete_messages.append(event_message.id)
                    logger.info("Deleting messages: {}".format(self.delete_messages))
                    result = await client.delete_messages(entity=self.channel_id, message_ids=self.delete_messages)
                except Exception as ex:
                    logger.exception(ex)

                if attackers:
                    final_text = client.translator.getLangTranslation(self.lang, 'EVENT_PUMPKIN_SILENT_FAILURE')
                else:
                    self.channel_size = await client.get_group_member_count(int(self.channel_id))
                    final_text = client.translator.getLangTranslation(self.lang, 'EVENT_PUMPKIN_SILENT_SUCCESS').format(member_count=self.channel_size, reward=reward)
                    await client.db.add_currency_to_all_chat_users(HalloweenConfig.currency_key, event_message.to_id.channel_id, reward)
                    client.loop.create_task(self.publish_pumpkin_amount_update(0))

                try:
                    await client.send_message(self.channel_id, final_text)
                except Exception as ex:
                    logger.exception(ex)

                break
            await asyncio.sleep(2)

    async def pumpkin_number_info_updater(self, client, event_message):
        self.client = client
        start_ts = datetime.utcnow()
        expected_number = randint(HalloweenConfig.number_range_min, HalloweenConfig.number_range_max)
        client.logger.info('Starting pumpkin_number_info_updater for message {} in channel {}, expected_number={}'.format(event_message.id, self.channel_id, expected_number))
        default_text = client.translator.getLangTranslation(self.lang, 'EVENT_PUMPKIN_NUMBER_INFO')
        last_text = ""
        info_message = None
        alive_seconds = randint(60, 180)
        reward = 5

        while True:
            await asyncio.sleep(1)

            if start_ts + timedelta(seconds=alive_seconds) < datetime.utcnow():
                self.calc_next_number_spawn()
                self.pumpkins[event_message.id].kill()

            attackers = self.get_attackers(event_message.id)
            if self.is_active(event_message.id):
                current_guesses = []
                for user_id in attackers.keys():
                    if attackers[user_id] not in current_guesses:
                        current_guesses.append(str(attackers[user_id]))

                new_text = default_text.format(min=HalloweenConfig.number_range_min, max=HalloweenConfig.number_range_max, total=len(attackers.keys()), current=' '.join(current_guesses))
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
                        logger.exception(ex)
            else:
                try:
                    self.delete_messages.append(info_message.id)
                    self.delete_messages.append(event_message.id)
                    logger.info("Deleting messages: {}".format(self.delete_messages))
                    result = await client.delete_messages(entity=self.channel_id, message_ids=self.delete_messages)
                except Exception as ex:
                    logger.exception(ex)

                self.delete_messages = []
                total = 0
                winners = 0

                if attackers is not None and not self.is_test(event_message.id):

                    for user_id in attackers.keys():
                        total += 1
                        if attackers[user_id] == expected_number:
                            winners += 1
                            await client.db.add_currency_to_user(HalloweenConfig.currency_key, user_id, reward)
                            client.loop.create_task(self.publish_pumpkin_amount_update(user_id))

                # If its not active anymore then post results
                if winners > 0:
                    final_text = client.translator.getLangTranslation(self.lang, 'EVENT_PUMPKIN_NUMBER_DIED_WON').format(correct=expected_number, winners=winners, total=total, reward=reward)
                else:
                    final_text = client.translator.getLangTranslation(self.lang, 'EVENT_PUMPKIN_NUMBER_DIED_NOBODY').format(correct=expected_number, total=total)

                # final_text += ' ' + HalloweenConfig.pumpkin_heart
                try:
                    await client.send_message(self.channel_id, final_text)
                except Exception as ex:
                    logger.exception(ex)

                break
            await asyncio.sleep(3)

    async def pumpkin_greedy_info_updater(self, client, sticker_message):
        self.client = client
        start_ts = datetime.utcnow()
        client.logger.info('Starting pumpkin_greedy_info_updater for message {} in channel {}'.format(sticker_message.id, self.channel_id))
        default_text = client.translator.getLangTranslation(self.lang, 'EVENT_PUMPKIN_GREEDY_INFO')
        last_text = ""
        info_message = None
        alive_seconds = randint(60, 180)

        while True:
            await asyncio.sleep(1)

            if start_ts + timedelta(seconds=alive_seconds) < datetime.utcnow():
                self.calc_next_greedy_spawn()
                self.pumpkins[sticker_message.id].kill()

            attackers = self.get_attackers(sticker_message.id)
            if self.is_active(sticker_message.id):
                new_text = default_text.format(emotes=' '.join([HalloweenConfig.greedy_message_a, HalloweenConfig.greedy_message_b]), total=len(attackers.keys()))
                if new_text == last_text:
                    continue
                else:
                    try:
                        last_text = new_text
                        if info_message is None:
                            info_message = await client.send_message(self.channel_id, new_text, reply_to=sticker_message.id)
                        else:
                            await info_message.edit(new_text)
                    except Exception as ex:
                        logger.exception(ex)
            else:
                try:
                    self.delete_messages.append(info_message.id)
                    self.delete_messages.append(sticker_message.id)
                    logger.info("Deleting messages: {}".format(self.delete_messages))
                    result = await client.delete_messages(entity=self.channel_id, message_ids=self.delete_messages)
                except Exception as ex:
                    logger.exception(ex)

                self.delete_messages = []
                total = 0
                group_a = []
                group_b = []
                if attackers is not None and not self.is_test(sticker_message.id):
                    for user_id in attackers.keys():
                        total += 1
                        if attackers.get(user_id) == 1:
                            group_a.append(user_id)
                        elif attackers.get(user_id) == 2:
                            group_b.append(user_id)

                if len(group_a + group_b) != total:
                    self.get_logger().error("Something is wrong, incorrect grouping of teams. team_a = {}, team_b = {}, total = {}".format(group_a, group_b, attackers))

                final_text = ''
                if len(group_a) == 0 and len(group_b) == 0:
                    self.channel_size = await client.get_group_member_count(int(self.channel_id))
                    await client.db.add_currency_to_all_chat_users(HalloweenConfig.currency_key, sticker_message.to_id.channel_id, -3)
                    client.loop.create_task(self.publish_pumpkin_amount_update(0))
                    final_text = client.translator.getLangTranslation(self.lang, 'EVENT_PUMPKIN_GREEDY_EMPTY_TEAMS').format(total=self.channel_size, amt=3)
                elif len(group_b) == len(group_a):
                    for user_id in group_a + group_b:
                        await client.db.add_currency_to_user(HalloweenConfig.currency_key, user_id, -2)
                        client.loop.create_task(self.publish_pumpkin_amount_update(user_id))
                    final_text = client.translator.getLangTranslation(self.lang, 'EVENT_PUMPKIN_GREEDY_EQUAL_TEAMS').format(total=total, amt=2)
                elif len(group_b) < len(group_a):
                    for user_id in group_b:
                        await client.db.add_currency_to_user(HalloweenConfig.currency_key, user_id, 2)
                        client.loop.create_task(self.publish_pumpkin_amount_update(user_id))
                    for user_id in group_a:
                        await client.db.add_currency_to_user(HalloweenConfig.currency_key, user_id, -2)
                        client.loop.create_task(self.publish_pumpkin_amount_update(user_id))
                    final_text = client.translator.getLangTranslation(self.lang, 'EVENT_PUMPKIN_GREEDY_TEAM_WON').format(team=HalloweenConfig.greedy_message_b, amt=2)
                elif len(group_b) > len(group_a):
                    for user_id in group_a:
                        await client.db.add_currency_to_user(HalloweenConfig.currency_key, user_id, 2)
                        client.loop.create_task(self.publish_pumpkin_amount_update(user_id))
                    for user_id in group_b:
                        await client.db.add_currency_to_user(HalloweenConfig.currency_key, user_id, -2)
                        client.loop.create_task(self.publish_pumpkin_amount_update(user_id))
                    final_text = client.translator.getLangTranslation(self.lang, 'EVENT_PUMPKIN_GREEDY_TEAM_WON').format(team=HalloweenConfig.greedy_message_a, amt=2)

                final_text += ' ' + HalloweenConfig.pumpkin_greedy
                try:
                    await client.send_message(self.channel_id, final_text)
                except Exception as ex:
                    logger.exception(ex)

                break

            await asyncio.sleep(3)

    async def pumpkin_love_info_updater(self, client, love_message):
        self.client = client
        start_ts = datetime.utcnow()
        client.logger.info('Starting pumpkin_love_info_updater for message {} in channel {}'.format(love_message.id, self.channel_id))
        default_text = client.translator.getLangTranslation(self.lang, 'EVENT_PUMPKIN_LOVE_INFO')
        last_text = ""
        info_message = None
        alive_seconds = randint(60, 180)

        while True:
            await asyncio.sleep(1)

            if start_ts + timedelta(seconds=alive_seconds) < datetime.utcnow():
                self.calc_next_love_spawn()
                self.pumpkins[love_message.id].kill()

            attackers = self.get_attackers(love_message.id)
            if self.is_active(love_message.id):
                new_text = default_text.format(emotes=' '.join(HalloweenConfig.love_messages), total=len(attackers.keys()))
                if new_text == last_text:
                    continue
                else:
                    try:
                        last_text = new_text
                        if info_message is None:
                            info_message = await client.send_message(self.channel_id, new_text, reply_to=love_message.id)
                        else:
                            await info_message.edit(new_text)
                    except Exception as ex:
                        logger.exception(ex)
            else:
                try:
                    self.delete_messages.append(info_message.id)
                    self.delete_messages.append(love_message.id)
                    logger.info("Deleting messages: {}".format(self.delete_messages))
                    result = await client.delete_messages(entity=self.channel_id, message_ids=self.delete_messages)
                except Exception as ex:
                    logger.exception(ex)

                self.delete_messages = []
                total = 0
                if attackers is not None and not self.is_test(love_message.id):
                    for user_id in attackers.keys():
                        total += 1
                        await client.db.add_currency_to_user(HalloweenConfig.currency_key, user_id, 1)
                        client.loop.create_task(self.publish_pumpkin_amount_update(user_id))

                # If its not active anymore then post results
                final_text = client.translator.getLangTranslation(self.lang, 'EVENT_PUMPKIN_LOVE_DIED').format(total=total)
                final_text += ' ' + HalloweenConfig.pumpkin_heart
                try:
                    await client.send_message(self.channel_id, final_text)
                except Exception as ex:
                    logger.exception(ex)

                break

            await asyncio.sleep(3)

    async def pumpkin_scary_info_updater(self, client, event_message):
        self.client = client
        start_ts = datetime.utcnow()
        client.logger.info('Starting pumpkin_scary_info_updater for message {} in channel {}'.format(event_message.id, self.channel_id))
        default_text = client.translator.getLangTranslation(self.lang, 'EVENT_PUMPKIN_SCARY_INFO')
        last_text = ""
        info_message = None
        alive_seconds = randint(60, 180)

        while True:
            await asyncio.sleep(1)

            if start_ts + timedelta(seconds=alive_seconds) < datetime.utcnow():
                self.calc_next_scary_spawn()
                self.pumpkins[event_message.id].kill()

            attackers = self.get_attackers(event_message.id)
            if self.is_active(event_message.id):
                new_text = default_text.format(emotes=' '.join(HalloweenConfig.scary_messages), total=len(attackers.keys()))
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
                        logger.exception(ex)
            else:
                try:
                    self.delete_messages.append(info_message.id)
                    self.delete_messages.append(event_message.id)
                    logger.info("Deleting messages: {}".format(self.delete_messages))
                    result = await client.delete_messages(entity=self.channel_id, message_ids=self.delete_messages)
                except Exception as ex:
                    logger.exception(ex)

                self.delete_messages = []
                total = 0
                if attackers is not None and not self.is_test(event_message.id):
                    for user_id in attackers.keys():
                        total += 1
                        await client.db.add_currency_to_user(HalloweenConfig.currency_key, user_id, 1)
                        client.loop.create_task(self.publish_pumpkin_amount_update(user_id))

                # If its not active anymore then post results
                if total > 0:
                    final_text = client.translator.getLangTranslation(self.lang, 'EVENT_PUMPKIN_SCARY_DIED_SUCCESS').format(total=total)
                else:
                    final_text = client.translator.getLangTranslation(self.lang, 'EVENT_PUMPKIN_SCARY_DIED_FAILURE')

                final_text += ' ' + HalloweenConfig.pumpkin_scary
                try:
                    await client.send_message(self.channel_id, final_text)
                except Exception as ex:
                    logger.exception(ex)

                break

            await asyncio.sleep(3)

    async def pumpkin_chestbox_info_updater(self, client, chest_message):
        self.client = client
        client.logger.info('Starting pumpkin_chextbox_info_updater for boss message {} in channel {}'.format(chest_message.id, self.channel_id))
        default_text = client.translator.getLangTranslation(self.lang, 'EVENT_PUMPKIN_CHESTBOX_INFO')
        last_text = ""
        info_message = None

        while True:
            await asyncio.sleep(1)

            tries = self.get_boss_max_hp(chest_message.id) - 1

            if self.is_active(chest_message.id):
                new_text = default_text.format(emotes=' '.join(HalloweenConfig.chestbox_keys), tries=tries)
                if new_text == last_text:
                    continue
                else:
                    try:
                        last_text = new_text
                        if info_message is None:
                            info_message = await client.send_message(self.channel_id, new_text, reply_to=chest_message.id)
                        else:
                            await info_message.edit(new_text)
                    except Exception as ex:
                        logger.exception(ex)
            else:
                try:
                    self.delete_messages.append(info_message.id)
                    logger.info("Deleting messages: {}".format(self.delete_messages))
                    result = await client.delete_messages(entity=self.channel_id, message_ids=self.delete_messages)
                except Exception as ex:
                    logger.exception(ex)

                self.delete_messages = []
                attackers = self.get_attackers(chest_message.id)
                addon = int(tries / 2)
                roll = HalloweenConfig.roll_incremental(2 + addon, max(4, tries))
                user_id = None
                for attacker in attackers.keys():
                    user_id = int(attacker)
                    break
                sender = None
                if user_id is not None:
                    sender = await get_first(await client.db.getResponseByUserId(user_id))
                    if sender is None:
                        client.logger.info('Failed to find sender by user ID {}'.format(user_id))

                    if not self.is_test(chest_message.id):
                        await client.db.add_currency_to_user(HalloweenConfig.currency_key, user_id, roll)
                        client.loop.create_task(self.publish_pumpkin_amount_update(user_id))
                else:
                    logger.warning('Failed to find user_id from chestbox attackers! attackers: {}'.format(attackers))

                if sender is not None:
                    sender_entity = await client.get_entity(int(sender['tg_id']))
                    sender_label = await format_html_user_mention(sender_entity)
                else:
                    sender_label = 'Unknown'

                text = client.translator.getLangTranslation(self.lang, 'GLOBAL_HALLOWEEN_CHESTBOX_DESTROY')
                text = text.format(roll=roll, user=sender_label, tries=tries)
                text += ' 👻'

                try:
                    await client.send_message(self.channel_id, text)
                    if self.next_box < datetime.utcnow():
                        self.calc_next_box_spawn()
                except Exception as ex:
                    logger.exception(ex)
                break

            await asyncio.sleep(3)

    async def pumpkin_boss_info_updater(self, client, boss_message):
        client.logger.info('Starting pumpkin_boss_info_updater for boss message {} in channel {}'.format(boss_message.id, self.channel_id))
        self.client = client
        default_text = client.translator.getLangTranslation(self.lang, 'EVENT_PUMPKIN_BOSS_INFO')
        last_text = ""
        info_message = None
        started_at = datetime.utcnow()

        while True:
            if started_at + timedelta(minutes=15) < datetime.utcnow():
                try:
                    if info_message is not None:
                        self.delete_messages.append(info_message.id)
                    self.delete_messages.append(boss_message.id)
                    self.delete(boss_message.id)
                    logger.info("Expired boss. Deleting messages: {}".format(self.delete_messages))
                    result = await client.delete_messages(entity=self.channel_id, message_ids=self.delete_messages)
                except Exception as ex:
                    logger.exception(ex)
                break

            await asyncio.sleep(1)
            last_hp = self.get_boss_hp(boss_message.id)
            full_hp = self.get_boss_max_hp(boss_message.id)
            last_fighters = self.get_boss_fighters_unique_count(boss_message.id)

            if self.is_active(boss_message.id):
                new_text = default_text.format(emotes=' '.join(HalloweenConfig.hit_message), hp=last_hp, fighters=last_fighters)
                new_text += HalloweenConfig.format_boss_hp_bar(last_hp, full_hp)
                if new_text == last_text:
                    continue
                else:
                    try:
                        last_text = new_text
                        if info_message is None:
                            info_message = await client.send_message(self.channel_id, new_text, reply_to=boss_message.id)
                        else:
                            await info_message.edit(new_text)
                    except Exception as ex:
                        logger.exception(ex)
            else:
                self.calc_next_boss_spawn()
                try:
                    self.delete_messages.append(info_message.id)
                    logger.info("Deleting messages: {}".format(self.delete_messages))
                    result = await client.delete_messages(entity=self.channel_id, message_ids=self.delete_messages)
                except Exception as ex:
                    logger.exception(ex)

                self.delete_messages = []
                total = 0
                attackers = self.get_attackers(boss_message.id)

                if attackers is not None and not self.is_test(boss_message.id):
                    for user_id in attackers.keys():
                        count = min(attackers[user_id], 3)
                        total += count
                        await client.db.add_currency_to_user(HalloweenConfig.currency_key, user_id, count)
                        client.loop.create_task(self.publish_pumpkin_amount_update(user_id))

                # If its not active anymore then post results
                final_text = client.translator.getLangTranslation(self.lang, 'EVENT_PUMPKIN_BOSS_DIED').format(pumpkins=total, fighters=last_fighters)
                try:
                    await client.send_message(self.channel_id, final_text)
                except Exception as ex:
                    logger.exception(ex)

                break

            await asyncio.sleep(3)

    def get_boss_hp(self, msg_id: int)->int:
        if msg_id not in self.pumpkins:
            return 0

        return max(self.pumpkins[msg_id].current_hp, 0)

    def get_boss_max_hp(self, msg_id: int)->int:
        if msg_id not in self.pumpkins:
            return 0

        return max(self.pumpkins[msg_id].max_hp, 0)

    def get_boss_fighters_unique_count(self, msg_id: int)->int:
        if msg_id not in self.pumpkins:
            return 0

        unique_list = []

        for user in self.pumpkins[msg_id].damagers:
            if user in unique_list:
                continue

            unique_list.append(user)

        return len(unique_list)

    async def publish_pumpkin_amount_update(self, user_id: int):
        if not self.client:
            return

        if user_id == 0:
            # TODO: 0 means added to all
            return

        currency_data = await get_first(await self.client.db.get_user_currency_amount(HalloweenConfig.currency_key, user_id))
        if currency_data is None:
            return

        user_data = await get_first(await self.client.db.getUserById(user_id))
        if user_data is None:
            return

        body = {
            'name': user_data['name'],
            'dname': user_data['dname'],
            'amount': int(currency_data['amount'])
        }

        await self.client.db.redis.publish_event(redis_key.get_halloween_update_topic(), body)


class HalloweenConfig:
    pumpkin_message: str = "🎃"
    pumpkin_boss = "🤬"
    pumpkin_heart = '😘'
    pumpkin_number = '🤔'
    pumpkin_silent = '💑'
    pumpkin_scary = '👻'
    pumpkin_greedy = '😈'
    chestbox = "📦"
    chestbox_keys = ["🗝", "🔑"]
    hit_message: List[str] = ["🪓", "🔨", "🗡", "🔪", "🏹", "🔫"]
    love_messages: List[str] = ["❤️", "🧡", "💛", "💚", "💙", "💜", "🖤", "🤍", "🤎"]
    scary_messages: List[str] = ['😨', '😱']
    greedy_message_a: str = '🅰️'
    greedy_message_b: str = '🅱️'
    currency_key: str = "pumpkin_2021"
    number_range_min = 1
    number_range_max = 7

    @staticmethod
    def is_event_regular(message)->bool:
        return message.text == HalloweenConfig.pumpkin_message

    @staticmethod
    def is_event_boss(message)->bool:
        if not message.sticker:
            return False

        for attr in message.media.document.attributes:
            if isinstance(attr, DocumentAttributeSticker) and attr.stickerset.id == 773947703670341645 and attr.alt == HalloweenConfig.pumpkin_boss:
                return True

        return False

    @staticmethod
    def is_event_love(message)->bool:
        if not message.sticker:
            return False

        for attr in message.media.document.attributes:
            if isinstance(attr, DocumentAttributeSticker) and attr.stickerset.id == 773947703670341645 and attr.alt == HalloweenConfig.pumpkin_heart:
                return True

        return False

    @staticmethod
    def is_event_greedy(message)->bool:
        if not message.sticker:
            return False

        for attr in message.media.document.attributes:
            if isinstance(attr, DocumentAttributeSticker) and attr.stickerset.id == 891885078961979404 and attr.alt == HalloweenConfig.pumpkin_greedy:
                return True

        return False

    @staticmethod
    def is_event_scary(message)->bool:
        if not message.sticker:
            return False

        for attr in message.media.document.attributes:
            if isinstance(attr, DocumentAttributeSticker) and attr.stickerset.id == 773947703670341645 and attr.alt == HalloweenConfig.pumpkin_scary:
                return True

        return False

    @staticmethod
    def is_event_box(message)->bool:
        if not message.sticker:
            return False

        for attr in message.media.document.attributes:
            if isinstance(attr, DocumentAttributeSticker) and attr.stickerset.id == 3293761443790323713 and attr.alt == HalloweenConfig.chestbox:
                return True

        return False

    @staticmethod
    def is_event_number(message)->bool:
        if not message.sticker:
            return False

        for attr in message.media.document.attributes:
            if isinstance(attr, DocumentAttributeSticker) and attr.stickerset.id == 773947703670341645 and attr.alt == HalloweenConfig.pumpkin_number:
                return True

        return False

    @staticmethod
    def is_event_reply(message)->bool:
        return message.text in HalloweenConfig.hit_message

    @staticmethod
    def is_event_box_reply(message)->bool:
        return message.text in HalloweenConfig.chestbox_keys

    @staticmethod
    def is_event_love_reply(message)->bool:
        return message.text in HalloweenConfig.love_messages

    @staticmethod
    def is_event_greedy_reply(message)->bool:
        return message.text in [HalloweenConfig.greedy_message_a, HalloweenConfig.greedy_message_b]

    @staticmethod
    def is_event_scary_reply(message)->bool:
        if message.sticker:
            for attr in message.media.document.attributes:
                if isinstance(attr, DocumentAttributeSticker) and attr.alt in HalloweenConfig.scary_messages:
                    return True
            return False

        return message.text in HalloweenConfig.scary_messages

    @staticmethod
    def is_event_number_reply(message)->bool:
        try:
            parsed = int(message.text)
        except ValueError:
            parsed = -1

        return HalloweenConfig.number_range_min <= parsed <= HalloweenConfig.number_range_max

    @staticmethod
    def calc(amt: int, limit: int=500) -> int:
        calc_ratio = math.log((amt + (amt / 5)) / 100000000)
        calc_ratio = calc_ratio * calc_ratio / amt * 100
        return min(int(calc_ratio), limit)

    @staticmethod
    def calc_boss_hp(size: int)->int:
        a = size / 2
        b = a / 2
        c = randint(int(b), int(a))
        return max(int(min(c, 30)), 3)

    @staticmethod
    def format_boss_hp_bar(hp: int, max_hp: int)->str:
        bar_red = "🟥"
        bar_yellow = "🟧"
        bar_green = "🟩"

        ratio = hp / max_hp
        if ratio > 0.5:
            bar_active = bar_green
        elif ratio > 0.25:
            bar_active = bar_yellow
        else:
            bar_active = bar_red

        bar_count = int(math.ceil(ratio * 10))

        hp_bar = ""
        for i in range(1, bar_count + 1):
            hp_bar += bar_active

        return hp_bar

    @staticmethod
    def roll_incremental(current: int, max_damage: int)->int:
        if current >= max_damage:
            return max_damage

        increase: bool = bool(randint(0, 1))
        if not increase:
            return current

        current += 1
        return HalloweenConfig.roll_incremental(current, max_damage)
