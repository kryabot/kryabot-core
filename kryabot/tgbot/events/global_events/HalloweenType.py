import asyncio
import logging
import math
from datetime import datetime, timedelta
from typing import Dict, List
from random import randint

from telethon import utils
from telethon.tl.types import DocumentAttributeSticker

from object.Base import Base

logger: logging = logging.getLogger('krya.tg')


class HalloweenChannels(Base):
    def __init__(self):
        self.channels: Dict[int, HalloweenChannel] = {}

    def new_channel(self, channel_id, lang):
        self.channels[channel_id] = HalloweenChannel(channel_id, lang)

    def new_spawn(self, channel_id, message_id):
        self.channels[channel_id].save(message_id)

    def is_active(self, channel_id, message_id)->bool:
        return self.channels[channel_id].is_active(message_id)

    def hit_pumkin(self, channel_id: int, message_id: int, user_id: int)->bool:
        channel: HalloweenChannel = self.channels[channel_id]
        return channel.hit_pumpkin(message_id, user_id)


class HalloweenChannel(Base):
    def __init__(self, channel_id, lang):
        self.channel_id: int = channel_id
        self.lang: str = lang
        self.pumpkins: Dict[int, Pumpkin] = {}
        self.last_regular: datetime = datetime.utcnow()
        self.last_boss: datetime = datetime.utcnow()

    def is_active(self, msg_id: int)->bool:
        if not int(msg_id) in self.pumpkins:
            return False

        return self.pumpkins[int(msg_id)].active

    def has_active_pumpkin(self)->bool:
        for key in self.pumpkins.keys():
            if self.pumpkins[key] is not None and self.pumpkins[key].active:
                return True

        return False

    def hit_pumpkin(self, msg_id: int, user_id: int)->bool:
        if not msg_id in self.pumpkins:
            return False

        logger.info("Pumking {} was hit after {} seconds by {}".format(msg_id, (datetime.utcnow() - self.pumpkins[int(msg_id)].created).seconds, user_id))
        pumpkin: Pumpkin = self.pumpkins[msg_id]
        return pumpkin.hit(user_id)

    def can_spawn_boss(self, channel_size: int) -> bool:
        if channel_size < 20:
            return False

        if self.has_active_pumpkin():
            logger.info("Skipping spawn of boss in {} because still have active".format(self.channel_id))
            return False

        ratio = HalloweenConfig.calc(channel_size)
        min_time = max(int(ratio), 5)
        max_time = max(int(ratio), 15)
        logger.info('Result min: {} max: {} for size {}'.format(min_time, max_time, channel_size))

        delay = randint(min_time, max_time)
        if self.last_boss + timedelta(minutes=delay) < datetime.utcnow():
            return True

        return False

    def can_spawn_regular(self, channel_size: int)->bool:
        if self.has_active_pumpkin():
            logger.info("Skipping spawn of regular in {} because still have active".format(self.channel_id))
            return False

        ratio = HalloweenConfig.calc(channel_size)
        min_time = max(int(ratio * 7), 60)
        max_time = max(int(ratio * 7), 180)
        logger.info('Result min: {} max: {} for size {}'.format(min_time, max_time, channel_size))

        delay = randint(min_time, max_time)
        if self.last_regular + timedelta(minutes=delay) < datetime.utcnow():
            return True

        return False

    def save(self, msg_id: int, boss=False):
        self.pumpkins[int(msg_id)] = Pumpkin(msg_id, boss=boss)

    async def spawn_regular(self, client):
        self.last_regular = datetime.utcnow()
        msg = await client.send_message(self.channel_id, HalloweenConfig.pumpkin_message)
        client.logger.info("Spawned regular pumpkin ID {} in channel {}".format(msg.id, self.channel_id))
        self.save(msg.id)

    async def spawn_boss(self, client):
        self.last_boss = datetime.utcnow()
        msg = await self.send_halloween_sticker(client, self.channel_id, HalloweenConfig.pumkin_boss)
        client.logger.info("Spawned boss pumpkin ID {} in channel {}".format(msg.id, self.channel_id))
        self.save(msg.id, boss=True)
        client.loop.create_task(self.pumpkin_boss_info_updater(client, msg))

    async def send_halloween_sticker(self, client, channel_id, emote):
        kryabot_stickers = await client.get_sticker_set('Halloweenkin')
        for sticker in kryabot_stickers.packs:
            if sticker.emoticon == emote:
                for pack in kryabot_stickers.documents:
                    if sticker.documents[0] == pack.id:
                        return await client.send_file(channel_id, pack)

    def get_attackers(self, msg_id: int):
        if msg_id not in self.pumpkins:
            return None

        return self.pumpkins[msg_id].damagers

    async def pumpkin_boss_info_updater(self, client, boss_message):
        default_text = client.translator.getLangTranslation(self.lang, 'EVENT_PUMPKIN_BOSS_INFO')
        last_text = ""
        info_message = None

        while True:
            await asyncio.sleep(1)
            last_hp = self.get_boss_hp(boss_message.id)
            last_fighters = self.get_boss_fighters_unique_count(boss_message.id)

            if self.is_active(boss_message.id):
                new_text = default_text.format(emotes=' '.join(HalloweenConfig.hit_message), hp=last_hp, fighters=last_fighters)
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
                total = 0
                attackers = self.get_attackers(boss_message.id)

                if attackers is not None:
                    for user_id in attackers.keys():
                        count = min(attackers[user_id], 3)
                        total += count
                        await client.db.add_currency_to_user(HalloweenConfig.currency_key, user_id, count)

                # If its not active anymore then post results, wait a bit and clean up
                final_text = client.translator.getLangTranslation(self.lang, 'EVENT_PUMPKIN_BOSS_DIED').format(pumpkins=total, fighters=last_fighters)
                try:
                    await info_message.edit(final_text)
                except Exception as ex:
                    logger.exception(ex)

                await asyncio.sleep(60)
                try:
                    await info_message.delete()
                except:
                    pass
                break

            await asyncio.sleep(3)

    def get_boss_hp(self, msg_id: int)->int:
        if not msg_id in self.pumpkins:
            return 0

        return max(self.pumpkins[msg_id].hp, 0)

    def get_boss_fighters_unique_count(self, msg_id: int)->int:
        if not msg_id in self.pumpkins:
            return 0

        unique_list = []

        for user in self.pumpkins[msg_id].damagers:
            if user in unique_list:
                continue

            unique_list.append(user)

        return len(unique_list)


class Pumpkin(Base):
    def __init__(self, msg_id: int, boss=False):
        self.msg_id: int = msg_id
        self.active: bool = True
        self.created: datetime = datetime.utcnow()
        self.last_activity: datetime = datetime.utcnow()
        self.boss: bool = boss
        self.hp: int = 10 if self.boss else 1
        self.damagers: Dict[int, int] = {}

    def hit(self, user_id: int, dmg: int = 1)->bool:
        if not self.active:
            return False

        # Reduce HP
        self.hp -= dmg
        self.last_activity: datetime = datetime.utcnow()

        if user_id in self.damagers:
            self.damagers[user_id] += dmg
        else:
            self.damagers[user_id] = dmg

        # Last hit
        if self.hp <= 0:
            self.active = False
            return True

        return False


class HalloweenConfig:
    pumpkin_message: str = "🎃"
    pumkin_boss = "🤬"
    hit_message: List[str] = ["🪓", "🔨", "🗡", "🔪", "🏹", "⚔️", "🔫"]
    currency_key: str = "pumpkin"

    @staticmethod
    def is_event_regular(message)->bool:
        return message.text == HalloweenConfig.pumpkin_message

    @staticmethod
    def is_event_boss(message)->bool:
        if not message.sticker:
            return False

        for attr in message.media.document.attributes:
            if isinstance(attr, DocumentAttributeSticker) and attr.stickerset.id == 773947703670341645 and attr.alt == HalloweenConfig.pumkin_boss:
                return True

        return False

    @staticmethod
    def is_event_reply(message)->bool:
        return message.text in HalloweenConfig.hit_message

    @staticmethod
    def calc(amt: int) -> int:
        calc_ratio = math.log((amt + (amt / 5)) / 100000000)
        calc_ratio = calc_ratio * calc_ratio / amt * 100
        return min(int(calc_ratio), 500)
