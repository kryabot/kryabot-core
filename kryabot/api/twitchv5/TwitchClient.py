from api.core import Core
import api.twitchv5.exception as ex
from api.twitchv5.topics.Bits import Bits
from api.twitchv5.topics.Channel import Channel
from api.twitchv5.topics.Games import Games
from api.twitchv5.topics.Moderation import Moderation
from api.twitchv5.topics.Stream import Stream
from api.twitchv5.topics.User import User
from object.RedisHelper import RedisHelper
from utils.constants import BOT_TWITCH_ID
from utils.twitch import get_active_app_token
import utils.redis_key as redis_key
from aiohttp import ClientResponseError, ClientResponse

import asyncio


class TwitchClient(Core, User, Stream, Bits, Games, Moderation, Channel):
    def __init__(self):
        super().__init__()
        self.client_id = self.cfg.getTwitchConfig()['API_KEY']
        self.client_secret = self.cfg.getTwitchConfig()['SECRET']
        self.token_url = 'https://id.twitch.tv/oauth2/token'
        self.helix_url = 'https://api.twitch.tv/helix/'
        self._redis = RedisHelper.get_instance()

    async def get_headers(self, oauth_token=None):
        return await self.get_json_headers(oauth_token=oauth_token)

    async def get_json_headers(self, oauth_token=None, bearer_token=None, add_auth=True):
        headers = {
            'Accept': 'application/json',
            'Client-ID': self.client_id
        }

        if add_auth:
            if oauth_token:
                headers['Authorization'] = 'OAuth {}'.format(oauth_token)
            else:
                if bearer_token is None:
                    bearer_token = await get_active_app_token(self)
                headers['Authorization'] = 'Bearer {}'.format(bearer_token)

        return headers

    @property
    def hostname(self) -> str:
        return self.helix_url

    @property
    def redis_keys(self):
        return redis_key

    @property
    def redis(self):
        return self._redis

    async def refresh_token(self, refresh_token):
        headers = await self.get_json_headers(add_auth=False)
        body = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
            'client_secret': self.client_secret,
            'client_id': self.client_id,
        }
        return await self.make_post_request(url=self.token_url, body=body, headers=headers)

    async def refresh_app_token(self):
        headers = await self.get_json_headers(add_auth=False)
        body = {
            'grant_type': 'client_credentials',
            'client_secret': self.client_secret,
            'client_id': self.client_id
        }
        return await self.make_post_request(url=self.token_url, body=body, headers=headers)

    async def is_bot_mod(self, broadcaster_id):
        # First output param indicates if we have right granted
        # Second output param indicates if we have mod status
        try:
            response = await self.get_moderators(broadcaster_id=broadcaster_id, user_id=BOT_TWITCH_ID)
            return True, response and len(response['data'])
        except Exception as err:
            self.logger.exception(err)
            # if there is an error, we dont care if we are mod or not
            return False, False

    async def get_channel_chatters(self, channel_name: str, skip_cache: bool = False):
        cache_key = redis_key.get_chatters(channel_name)
        data = None

        if self.redis is not None and not skip_cache:
            data = await self.redis.get_parsed_value_by_key(cache_key)

        if data is None:
            url = 'http://tmi.twitch.tv/group/user/{}/chatters'.format(channel_name)
            data = await self.make_get_request(url, headers={})
            if data is None:
                # Retry
                await asyncio.sleep(1)
                data = await self.make_get_request(url, headers={})

            if self.redis is not None:
                await self.redis.set_parsed_value_by_key(cache_key, data, expire=redis_key.ttl_minute)

        return data

    async def is_success(self, response: ClientResponse):
        try:
            return await super().is_success(response)
        except ClientResponseError as e:
            body = await response.json()
            if e.status == 401:
                raise ex.ExpiredAuthToken(body) from e
            else:
                if ex.AlreadyBannedError.matches(body):
                    raise ex.AlreadyBannedError(body) from e
                elif ex.AddVipRequestNoAvailableVipSlots.matches(body):
                    raise ex.AddVipRequestNoAvailableVipSlots(body) from e
                elif ex.UnvipRequestTargetNotVip.matches(body):
                    raise ex.UnvipRequestTargetNotVip(body) from e
                else:
                    raise ex.TwitchException(body) from e
