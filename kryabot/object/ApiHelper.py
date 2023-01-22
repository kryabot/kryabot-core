from api.betterttv import Betterttv
from api.boosty import Boosty
from api.frankerfacez import Frankerfacez
from api.instagram import Instagram
from api.twitch_events import TwitchEvents
from api.vk import VK
from api.twitchv5.TwitchClient import TwitchClient
from api.guardbot import GuardBot
from api.googlecloud import GoogleCloud
from api.yandex import Yandex
from object.Base import Base


class ApiHelper(Base):
    instance = None

    def __init__(self, reporter=None):
        self.vk = VK()
        self.twitch = TwitchClient()
        self.twitch_events = TwitchEvents()
        self.guardbot = GuardBot()
        self.gc = GoogleCloud()
        self.boosty = Boosty()
        self.instagram = Instagram()
        self.betterttv = Betterttv()
        self.frankerfacez = Frankerfacez()
        self.yandex = Yandex()
        self.logger = self.vk.logger
        self.reporter = reporter

    @staticmethod
    def get_instance():
        if not ApiHelper.instance:
            ApiHelper.instance = ApiHelper()

        return ApiHelper.instance

    async def get_vk_song(self, vk_user_id):
        response = await self.vk.get_song(vk_user_id)
        
        try:
            response = response['response']
            status = response[0]['status_audio']['artist'] + ' - ' + response[0]['status_audio']['title']
        except:
            status = ''

        return status

    # Little helper method to have True/False as output next to response
    async def is_sub_v3(self, channel, user):
        try:
            response = await self.twitch.get_channel_subs(broadcaster_id=channel['tw_id'], users=[user['tw_id']])
            return len(response['data']) > 0, response, None
        except Exception as error:
            # TODO: use TwitchException instead of Exception
            return None, None, error
