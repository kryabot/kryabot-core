from api.betterttv import Betterttv
from api.boosty import Boosty
from api.frankerfacez import Frankerfacez
from api.instagram import Instagram
from api.twitch_events import TwitchEvents
from api.vk import VK
from api.twitch import Twitch
from api.guardbot import GuardBot
from api.googlecloud import GoogleCloud
from api.yandex import Yandex
from object.BotConfig import BotConfig

from utils.twitch import sub_check


class ApiHelper:
    def __init__(self, reporter=None, redis=None, cfg=None):
        if cfg is None:
            cfg = BotConfig()

        self.vk = VK(cfg=cfg)
        self.twitch = Twitch(redis=redis, cfg=cfg)
        self.twitch_events = TwitchEvents(redis=redis, cfg=cfg)
        self.guardbot = GuardBot(cfg=cfg)
        self.gc = GoogleCloud(cfg=cfg)
        self.boosty = Boosty(cfg=cfg)
        self.instagram = Instagram(cfg=cfg)
        self.betterttv = Betterttv(cfg=cfg)
        self.frankerfacez = Frankerfacez(cfg=cfg)
        self.yandex = Yandex(cfg=cfg)
        self.logger = self.vk.logger
        self.sub_check_false = 'sub_check_false'
        self.reporter = reporter
        self.redis = None

    # Twitch ids
    async def sub_check(self, auth_token, channel_id, users):
        try:
            response = await self.twitch.get_channel_subs(token=auth_token, channel_id=channel_id, users=users)
            return response, None
        except Exception as e:
            self.twitch.logger.error(str(e))
            # report any other unexpected error (unauthorized or forbidden etc)
            if self.reporter is not None:
                await self.reporter(e, 'Checking sub data for user {} in channel {}'.format(users, channel_id))
            return None, str(e)

    async def get_vk_song(self, vk_user_id):
        response = await self.vk.get_song(vk_user_id)
        
        try:
            response = response['response']
            status = response[0]['status_audio']['artist'] + ' - ' + response[0]['status_audio']['title']
        except:
            status = ''

        return status

    async def is_sub_v2(self, channel, user, db):
        response, error = await sub_check(channel, user, db, self)
        if error is None and response is not None and 'data' in response:
            return len(response['data']) > 0

        # Not sub
        if error is not None and error == self.sub_check_false:
            return False

        # Missing auth
        if error is not None and 'unauthorized' in error.lower():
            return None

        # if response is None:
        #     return False

        # Auth problems
        self.twitch.logger.critical(error)
        return None

    async def is_sub_v3(self, channel, user, db):
        response, error = await sub_check(channel, user, db, self)
        if error is None and response is not None and 'data' in response:
            return len(response['data']) > 0, response, error

        # Not sub
        if error is not None and error == self.sub_check_false:
            return False, response, error

        # Missing auth
        if error is not None and 'unauthorized' in error.lower():
            return None, response, error

        # if response is None:
        #     return False

        # Auth problems
        self.twitch.logger.critical(error)
        return None, response, error