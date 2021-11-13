from typing import List
import asyncio
import logging

from infobot.Event import Event
from infobot.KryaInfoBot import KryaInfoBot
from infobot.Listener import Listener
from infobot.Target import Target
from infobot.TargetLink import TargetLink
from infobot.boosty.BoostyListener import BoostyListener
from infobot.goodgame.GoodgameListener import GoodgameListener
from infobot.instagram.InstagramListener import InstagramListener
from infobot.twitch.TwitchListener import TwitchListener
from infobot.twitter.TwitterListener import TwitterListener
from infobot.vk.VkListener import VkListener
from infobot.wasd.WasdListener import WasdListener
from infobot.youtube.YoutubeListener import YoutubeListener
from infobot import UpdateBuilder
from object.ApiHelper import ApiHelper
from object.BotConfig import BotConfig
from object.Database import Database
from object.Pinger import Pinger
from object.System import System
from utils import redis_key


class TargetLinkList:
    def __init__(self):
        self.links: List[TargetLink] = []
        self.targets: List[Target] = []

    def get(self, infobot_id, link_table, link_id):
        return next(filter(
            lambda link: link.target_id == infobot_id and link.link_table == link_table and link.link_id == link_id,
            self.links), None)

    def add(self, link: TargetLink):
        self.remove(link.target_id, link.get_table(), link.link_id)
        self.links.append(link)

    def remove(self, infobot_id, link_table, link_id):
        existing = self.get(infobot_id, link_table, link_id)
        if not existing:
            return

        try:
            self.links.remove(existing)
        except ValueError:
            pass

    def get_target(self, target_id) -> Target:
        for target in self.targets:
            if int(target.target_id) == int(target_id):
                return target

        raise ValueError('Failed to find Target record for target_id={}'.format(target_id))

    def add_target(self, new_target: Target):
        self.targets = [target for target in self.targets if target.target_id != new_target.target_id]
        self.targets.append(new_target)


class InfoManager:
    def __init__(self, ):
        self.loop = asyncio.get_event_loop()
        self.cfg: BotConfig = BotConfig()
        self.db: Database = Database(self.loop, self.cfg.getTwitchConfig()['MAX_SQL_POOL'], cfg=self.cfg)
        self.api: ApiHelper = ApiHelper(cfg=self.cfg, redis=self.db.redis)
        self.logger: logging.Logger = logging.getLogger('krya.infomanager')

        # Target services
        self.tg_bot = KryaInfoBot(self)

        # self.targets: List[Target] = []
        self.links: TargetLinkList = TargetLinkList()

        # Source services
        self.listeners: List[Listener] = []

        # self.listeners.append(InstagramListener(self))
        self.listeners.append(TwitchListener(self))
        self.listeners.append(GoodgameListener(self))
        self.listeners.append(TwitterListener(self))
        self.listeners.append(VkListener(self))
        self.listeners.append(WasdListener(self))
        self.listeners.append(YoutubeListener(self))
        self.listeners.append(BoostyListener(self))

    async def start(self):
        await self.db.redis.connection_init()
        self.loop.create_task(self.db.redis.start_listener(self.subscribe))
        self.loop.create_task(Pinger(System.INFOMANAGER, self.logger, self.db.redis).run_task())

        await self.update()
        await self.start_services()

        for listener in self.listeners:
            await listener.start()
            self.loop.create_task(listener.listen())

        while True:
            await asyncio.sleep(5)

    async def start_services(self):
        await self.tg_bot.run()

    async def event(self, event: Event):
        self.logger.debug('Common event received')
        await event.save(self.db)

        links = []
        for link in self.links.links:
            if link.link_table == event.profile.link_table and link.link_id == event.profile.profile_id:
                links.append(link)

        if links:
            await self.process_event(links, event)

    async def subscribe(self):
        await self.db.redis.subscribe_event(redis_key.get_infobot_update_links_topic(), self.on_link_update)
        await self.db.redis.subscribe_event(redis_key.get_infobot_update_profile_topic(), self.on_profile_update)

    async def update(self):
        targets = await self.db.getAllActiveInfoBots()
        links = await self.db.getAllInfoBotLinks()

        for target in targets:
            t = Target(target)
            self.links.add_target(t)
            for link in links:
                if int(link['infobot_id']) == t.id:
                    l = TargetLink(link, t)
                    self.links.add(l)

    async def on_link_update(self, message):
        self.logger.info('Updating link: {}'.format(message))
        update: UpdateBuilder.LinkUpdate = UpdateBuilder.InfoBotUpdate.from_json(message)
        infobot_links = await self.db.getInfobotLinksByType(update.infobot_id, update.link_table)

        self.logger.info('Existing links: {}'.format(infobot_links))
        try:
            self.logger.info('Searching target for infobot ID {}'.format(update.infobot_id))
            target = self.links.get_target(update.infobot_id)
        except ValueError:
            self.logger.info('Search failed with ValueError')
            target_raw = await self.db.getInfobotById(update.infobot_id)
            target = Target(target_raw[0])
            self.links.add_target(target)

        if update.link_id:
            if update.action == UpdateBuilder.UpdateAction.UPDATE:
                link_raw = next(filter(
                    lambda link: link['link_id'] == update.link_id,
                    infobot_links), None)
                self.logger.info('Single Link raw: {}'.format(link_raw))
                if link_raw:
                    self.links.add(TargetLink(link_raw, target))
            else:
                self.links.remove(update.infobot_id, update.link_table, update.link_id)
        else:
            # Missing link_id should be only for adding, REMOVE must have value in update.link_id
            if update.action == UpdateBuilder.UpdateAction.UPDATE:
                for link_raw in infobot_links:
                    self.links.add(TargetLink(link_raw, target))

    async def on_profile_update(self, message):
        update_object = UpdateBuilder.InfoBotUpdate.from_json(message)
        for listener in self.listeners:
            await listener.push_update(update_object)

    async def on_exception(self, ex: Exception, info: str = ''):
        self.logger.error(info)
        self.logger.exception(ex)
        await self.tg_bot.exception_reporter(err=ex, info=info)

    async def process_event(self, links: List[TargetLink], event):
        tg_links = [link for link in links if link.target.is_target_telegram()]

        if tg_links:
            self.loop.create_task(self.tg_bot.info_event(tg_links, event))
