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
from object.ApiHelper import ApiHelper
from object.BotConfig import BotConfig
from object.Database import Database


class InfoManager:
    def __init__(self,):
        self.loop = asyncio.get_event_loop()
        self.cfg: BotConfig = BotConfig()
        self.db: Database = Database(self.loop, self.cfg.getTwitchConfig()['MAX_SQL_POOL'], cfg=self.cfg)
        self.api: ApiHelper = ApiHelper(cfg=self.cfg, redis=self.db.redis)
        self.logger: logging.Logger = logging.getLogger('krya.infomanager')

        # Target services
        self.tg_bot = KryaInfoBot(self)

        self.targets: List[Target] = []
        self.links: List[TargetLink] = []

        # Source services
        self.listeners: List[Listener] = []

        self.listeners.append(InstagramListener(self))
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

        targets = []
        for link in self.links:
            if link.link_table == event.profile.link_table and link.link_id == event.profile.profile_id:
                targets.append(link.target)

        if targets:
            await self.process_event(targets, event)
        else:
            self.logger.error('Received event, but no targets found:')
            self.logger.error(event.stringify())

    async def subscribe(self):
        await self.db.redis.subscribe_event('infobot.update', self.on_update)

    async def update(self):
        targets = await self.db.getAllActiveInfoBots()
        links = await self.db.getAllInfoBotLinks()

        self.links = []

        for target in targets:
            t = Target(target)
            for link in links:
                if int(link['infobot_id']) == t.id:
                    l = TargetLink(link, t)
                    self.links.append(l)

    async def on_update(self, message):
        await self.update()

        for listener in self.listeners:
            await listener.on_update(message)

    async def on_exception(self, ex: Exception, info: str=''):
        self.logger.error(info)
        self.logger.exception(ex)
        self.tg_bot.exception_reporter(err=ex, info=info)

    async def process_event(self, targets: List[Target], event):
        tg_targets = [t for t in targets if t.is_target_telegram()]

        if tg_targets:
            self.loop.create_task(self.tg_bot.info_event(tg_targets, event))
