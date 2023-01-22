import functools
from datetime import datetime, timedelta

from api.twitchv5.exception import ExpiredAuthToken
import object.ApiHelper as ah
import object.Database as database
from utils import redis_key
import asyncio

from utils.constants import BOT_TWITCH_ID, BOT_INTERNAL_ID


async def refresh_channel_token(channel, force_refresh=False):
    new_data = await get_active_oauth_data(channel['user_id'], force_refresh=force_refresh)
    db = database.Database.get_instance()
    channel = await db.get_auth_subchat(channel['tg_chat_id'])

    try:
        return channel[0]
    except IndexError:
        return channel


async def get_active_oauth_data_broadcaster(broadcaster_id: int, force_refresh: bool = False, sec_diff: int = 30):
    db = database.Database.get_instance()
    kb_user = await db.getUserRecordByTwitchId(broadcaster_id)
    if not kb_user or not kb_user[0]:
        raise IndexError('Failed to find kb user for twitch ID {}'.format(broadcaster_id))

    return await get_active_oauth_data(kb_user[0]['user_id'], force_refresh=force_refresh, sec_diff=sec_diff)


async def get_active_oauth_data(kb_user_id, force_refresh=False, sec_diff=30):
    db = database.Database.get_instance()
    api = ah.ApiHelper.get_instance()

    user = await db.getUserById(kb_user_id)
    if user is None or len(user) == 0:
        return None
    user = user[0]

    auth_data = await db.getBotAuthByUserId(kb_user_id=kb_user_id)
    if auth_data is None or len(auth_data) == 0:
        return None
    auth_data = auth_data[0]

    if auth_data['expires_at'] - timedelta(seconds=sec_diff) < datetime.now() or force_refresh is True:
        try:
            resp = await api.twitch.refresh_token(auth_data['refresh_token'])

            # Update in db
            await db.saveBotAuth(kb_user_id, resp['access_token'], resp['refresh_token'], resp['expires_in'])

            try:
                data = {"token": resp['access_token'], "tw_id": user['tw_id'], "scope": resp['scope']}
                await db.redis.publish_event(redis_key.get_token_update_topic(), data)
            except Exception as ex:
                db.logger.exception(ex)

            # Update in cache
            tg_chat = await db.getTgChatIdByUserId(kb_user_id)
            if tg_chat is None or len(tg_chat) == 0 or tg_chat[0]['tg_chat_id'] is None:
                pass
            else:
                await db.get_auth_subchat(tg_chat[0]['tg_chat_id'], skip_cache=True)

            auth_data = await db.getBotAuthByUserId(kb_user_id=kb_user_id)
            if auth_data is None or len(auth_data) == 0:
                return None
            auth_data = auth_data[0]
        except Exception as e:
            api.logger.error('On token refresh: {}'.format(str(e)))

    return auth_data


async def get_active_app_token(api, forced=False) -> str:
    if api.redis is None:
        raise Exception("Can not use get_active_app_token if redis is not enabled")

    token = None
    cache_key = redis_key.get_twitch_app_token()

    if not forced:
        token = await api.redis.get_value_by_key(cache_key)

    if token is None:
        api.logger.info('App token was not found in cache, generating new one')
        resp = await api.refresh_app_token()
        token = resp['access_token']
        expires_in = resp['expires_in']
        api.logger.info('Saving new generated token to cache')
        # Remove 1 day from expiration to avoid 401 errors during requests
        await api.redis.set_value_by_key(cache_key, token, expires_in - redis_key.ttl_day)

    return token


async def auth_request_with_retry(self, auth_id, request, *args, **kwargs):
    current_try = 0
    max_tries = 3

    auth_data = await get_active_oauth_data_broadcaster(auth_id)
    while True:
        current_try += 1
        if current_try > 1:
            await asyncio.sleep(current_try)

        if current_try == 2:
            auth_data = await get_active_oauth_data_broadcaster(auth_id)

        if current_try > 2:
            auth_data = await get_active_oauth_data_broadcaster(auth_id, force_refresh=True)

        try:
            kwargs['token'] = auth_data['token']
        except TypeError:
            ah.ApiHelper.get_instance().logger.error('Failed to get auth for user {} while executing {}'.format(auth_id, getattr(request, '__name__', 'Unknown')))
            continue

        try:
            return await request(self, *args, **kwargs)
        except ExpiredAuthToken as ex:
            if current_try > max_tries:
                raise ex
            continue


def app_auth():
    """
        Use with endpoints which require app access token.
        When expired, function will refresh app token and retry the call.
    """
    def decorator(f):
        @functools.wraps(f)
        async def decorated_function(self, *args, **kwargs):
            try:
                return await f(self, *args, **kwargs)
            except ExpiredAuthToken:
                await get_active_app_token(self, forced=True)
                return await f(self, *args, **kwargs)
        return decorated_function
    return decorator


def bot_auth():
    """
        Use with endpoints which require user token on behalf of bot account.
        Injects `token` parameter of bot account when it is not provided by consumer.
    """
    def decorator(f):
        @functools.wraps(f)
        async def decorated_function(self, *args, **kwargs):
            return await auth_request_with_retry(self, BOT_TWITCH_ID, f, *args, **kwargs)
        return decorated_function
    return decorator


def broadcaster_auth(key: str = 'broadcaster_id'):
    """
        Use with endpoints which require user token on behalf of broadcaster account.
        Injects `token` parameter of broadcaster account. Key value is Twitch user ID, by it we find required auth token.
    """
    def decorator(f):
        @functools.wraps(f)
        async def decorated_function(self, *args, **kwargs):
            broadcaster_id: int = int(kwargs.get(key))
            return await auth_request_with_retry(self, broadcaster_id, f, *args, **kwargs)
        return decorated_function
    return decorator


def inject_moderator():
    """
        Use with endpoints which require to do action on behalf of moderator (bot)
        Injects `moderator_id` parameter when it is not provided by consumer.
    """
    def decorator(f):
        @functools.wraps(f)
        async def decorated_function(self, *args, **kwargs):
            if 'moderator_id' not in kwargs or not kwargs['moderator_id']:
                kwargs['moderator_id'] = BOT_TWITCH_ID
            return await f(self, *args, **kwargs)
        return decorated_function
    return decorator


def _get_default_cursor(response):
    try:
        return response['pagination']['cursor']
    except KeyError:
        return None


def pagination(first: int = 1000, merge_array_key: str = 'data', extract_cursor: callable = _get_default_cursor):
    """
        Use with endpoints which uses pagination and and you always need all pages.
    """
    def decorator(f):
        @functools.wraps(f)
        async def decorated_function(self, *args, **kwargs):
            if 'first' not in kwargs:
                kwargs['first'] = first

            final_response = {}
            while True:
                current_response = await f(self, *args, **kwargs)
                if final_response:
                    current_response[merge_array_key] = final_response[merge_array_key] + current_response[merge_array_key]

                final_response = current_response

                cursor = extract_cursor(current_response)
                if not cursor:
                    break

                kwargs['after'] = cursor

            return final_response
        return decorated_function
    return decorator
