import asyncio
import functools

from aiohttp import ClientResponseError

from api.core import Core
from exceptions.twitch import ExpiredAuthToken
from utils.twitch import get_active_app_token
import utils.redis_key as redis_key


def app_auth():
    def decorator(f):
        @functools.wraps(f)
        async def decorated_function(self, *args, **kwargs):
            try:
                return await f(self, *args, **kwargs)
            except ExpiredAuthToken as ex:
                await get_active_app_token(self, forced=True)
                return await f(self, *args, **kwargs)
        return decorated_function
    return decorator


class Twitch(Core):
    def __init__(self, redis, cfg=None):
        super().__init__(cfg=cfg)
        self.client_id = self.cfg.getTwitchConfig()['API_KEY']
        self.client_secret = self.cfg.getTwitchConfig()['SECRET']
        self.token_url = 'https://id.twitch.tv/oauth2/token'
        self.base_url = 'https://api.twitch.tv/kraken/'
        self.helix_url = 'https://api.twitch.tv/helix/'
        self.callback_url = self.cfg.getInstanceConfig()['LOCALHOST'] + ':5050/twitch_callback'
        self.webhooks_url = 'https://api.twitch.tv/helix/webhooks/hub'
        self.remote_url = self.cfg.getKbApiConfig()['URL']
        self.remote_sub_endpoint = self.remote_url + self.cfg.getKbApiConfig()['CALLBACK_ENDPOINT_SUB']
        self.remote_stream_endpoint = self.remote_url + self.cfg.getKbApiConfig()['CALLBACK_ENDPOINT_STREAM']
        self.redis = redis
        self.webhook_secret = 'supermegasecret'

    async def get_headers(self, oauth_token=None):
        headers = {
            'Accept': 'application/vnd.twitchtv.v5+json',
            'Client-ID': self.client_id
        }

        if oauth_token:
            headers['Authorization'] = 'OAuth {}'.format(oauth_token)

        return headers

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
                    bearer_token = get_active_app_token(self)
                headers['Authorization'] = 'Bearer {}'.format(bearer_token)

        return headers

    async def get_user_by_name(self, username, skip_cache=False):
        cache_key = redis_key.get_api_tw_user_by_name(username)
        data = None

        if self.redis is not None and not skip_cache:
            data = await self.redis.get_parsed_value_by_key(cache_key)

        if data is None:
            url = '{base}users?login={uname}'.format(base=self.base_url, uname=username)
            data = await self.make_get_request(url)
            if self.redis is not None:
                await self.redis.set_parsed_value_by_key(cache_key, data, expire=redis_key.ttl_half_day)

        return data

    async def get_user_by_id(self, user_id, skip_cache=False):
        cache_key = redis_key.get_api_tw_user_by_id(user_id)
        data = None

        if self.redis is not None and not skip_cache:
            data = await self.redis.get_parsed_value_by_key(cache_key)

        if data is None:
            url = '{base}users/{id}'.format(base=self.base_url, id=user_id)
            data = await self.make_get_request(url)
            if self.redis is not None:
                await self.redis.set_parsed_value_by_key(cache_key, data, expire=redis_key.ttl_half_day)

        return data

    async def check_channel_following(self, channel_id, user_id):
        url = '{base}users/{uid}/follows/channels/{cid}'.format(base=self.base_url, uid=user_id, cid=channel_id)
        return await self.make_get_request(url)

    # OAuth required
    async def check_channel_subscribtion(self, token, channel_id, user_id):
        url = '{base}channels/{cid}/subscriptions/{uid}'.format(base=self.base_url, uid=user_id, cid=channel_id)
        return await self.make_get_request(url, token)

    async def webhook_subscribe(self, topic, user_id, channel_name, enable=True, lease_seconds=864000):
        topic_url = await self.get_webhook_topic_url(topic)
        topic_url = '{url}?user_id={id}'.format(url=topic_url, id=user_id)

        headers = await self.get_json_headers()
        body = {
            'hub.mode': await self.get_mode(enable),
            'hub.topic': topic_url,
            'hub.callback': self.remote_stream_endpoint + '?channel=' + user_id + '&topic=' + topic,
            'hub.lease_seconds': lease_seconds,
            'hub.secret': self.webhook_secret
        }

        return await self.make_post_request(url=self.webhooks_url, body=body, headers=headers)

    async def webhook_subscribe_stream(self, user_id, channel_name, enable=True):
        return await self.webhook_subscribe('streams', user_id, channel_name, enable)

    async def webhook_subscribe_subscribtion(self, user_id, token, enable=True, lease_seconds=864000):
        topic = 'subscriptions'
        topic_url = await self.get_webhook_topic_url(topic)
        topic_url = '{url}?broadcaster_id={id}&first=1'.format(url=topic_url, id=user_id)

        headers = await self.get_json_headers(bearer_token=token)
        body = {
            'hub.mode': await self.get_mode(enable),
            'hub.topic': topic_url,
            'hub.callback': '{}?topic={}&channel={}'.format(self.remote_sub_endpoint, topic, user_id),
            'hub.lease_seconds': lease_seconds,
            'hub.secret': self.webhook_secret
        }

        return await self.make_post_request(url=self.webhooks_url, body=body, headers=headers)

    async def get_mode(self, type):
        if type is None or type == True:
            return 'subscribe'
        return 'unsubscribe'

    async def get_webhook_topic_url(self, topicname):
        if topicname == 'follows':
            return 'https://api.twitch.tv/helix/users/follows'
        if topicname == 'streams':
            return 'https://api.twitch.tv/helix/streams'
        if topicname == 'user':
            return 'https://api.twitch.tv/helix/users'
        if topicname == 'game':
            return 'https://api.twitch.tv/helix/analytics/games'
        if topicname == 'extention':
            return 'https://api.twitch.tv/helix/analytics/extensions'
        if topicname == 'subscriptions':
            return 'https://api.twitch.tv/helix/subscriptions/events'
        return None

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

    async def get_streams(self, first=20, channel_name=None, after=None, before=None):
        url = '{base}streams?first={id}'.format(base=self.helix_url, id=first)

        if channel_name is not None:
            url = '{eurl}&user_login={ulog}'.format(eurl=url, ulog=channel_name)

        if after is not None:
            url = '{eurl}&after={valafter}'.format(eurl=url,valafter=after)

        if before is not None:
            url = '{eurl}&before={valbefore}'.format(eurl=url,valbefore=before)

        return await self.make_get_request(url)

    async def get_stream_info_by_id(self, twitch_user_id):
        url = '{base}streams?user_id={tuid}'.format(base=self.helix_url, tuid=twitch_user_id)

        return await self.make_get_request(url)

    @app_auth()
    async def get_stream_info_by_ids(self, twitch_user_ids, first=50, after=None, before=None):
        url = '{base}streams'.format(base=self.helix_url)

        params = [('user_id', x) for x in twitch_user_ids]

        if first is not None:
            params.append(('first', first))
        if after is not None:
            params.append(('after', after))
        if before is not None:
            params.append(('before', before))

        return await self.make_get_request(url=url, params=params)

    async def get_total_bits_by_user(self, broadcaster_tw_id, user_tw_id, token, period='all'):
        url = '{base}bits/leaderboard?count=1&user_id={user_id}&period={period}'.format(base=self.helix_url, user_id=user_tw_id, period=period)
        headers = await self.get_json_headers(bearer_token=token)

        return await self.make_get_request(url, headers=headers)

    async def get_bits_top(self, token, period='all', count=10):
        url = '{base}bits/leaderboard?count={cnt}&period={period}'.format(base=self.helix_url, cnt=count, period=period)
        headers = await self.get_json_headers(bearer_token=token)

        return await self.make_get_request(url, headers=headers)

    async def get_channel_chatters(self, channel_name: str, skip_cache: bool = False):
        cache_key = redis_key.get_chatters(channel_name)
        data = None

        if self.redis is not None and not skip_cache:
            data = await self.redis.get_parsed_value_by_key(cache_key)

        if data is None:
            url = 'http://tmi.twitch.tv/group/user/{}/chatters'.format(channel_name)
            data = await self.make_get_request(url)
            if data is None:
                # Retry
                await asyncio.sleep(1)
                data = await self.make_get_request(url)

            if self.redis is not None:
                await self.redis.set_parsed_value_by_key(cache_key, data, expire=redis_key.ttl_minute)

        return data

    @app_auth()
    async def get_game_info(self, game_id):
        key = redis_key.get_twitch_game_info(game_id)
        response = await self.redis.get_parsed_value_by_key(key)

        if response is None:
            headers = await self.get_json_headers()
            url = '{}games?id={}'.format(self.helix_url, game_id)
            response = await self.make_get_request(url, headers=headers)
            await self.redis.set_parsed_value_by_key(key, response, redis_key.ttl_month)

        return response

    async def is_success(self, response):
        try:
            return await super().is_success(response)
        except ClientResponseError as e:
            if e.status == 401:
                raise ExpiredAuthToken(e)
            else:
                raise e

