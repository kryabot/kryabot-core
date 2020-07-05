from datetime import datetime, timedelta
from utils import redis_key
import asyncio

async def refresh_channel_token_no_client(channel, db, api, force_refresh=False):
    new_data = await get_active_oauth_data(channel['user_id'], db, api, force_refresh=force_refresh)
    channel = await db.get_auth_subchat(channel['tg_chat_id'])

    try:
        return channel[0]
    except:
        return channel


async def refresh_channel_token(client, channel, force_refresh=False):
    return await refresh_channel_token_no_client(channel=channel, db=client.db, api=client.api, force_refresh=force_refresh)


async def sub_check(req_channel, requestor, db, api):
    req_channel = await refresh_channel_token_no_client(req_channel, db, api)

    if requestor['tw_id'] == 0:
        twitch_user = await api.twitch.get_user_by_name(requestor['name'])
        if twitch_user is None or len(twitch_user['users']) == 0:
            return None, "deleted_twitch_account"
        await db.updateUserTwitchId(requestor['user_id'], twitch_user['users'][0]['_id'])
        user_twitch_id = twitch_user['users'][0]['_id']
    else:
        user_twitch_id = requestor['tw_id']

    current_try = 0
    max_tries = 3

    sub_data = None
    sub_error = None

    while True:
        current_try += 1
        if current_try > max_tries:
            break

        if current_try > 1:
            await asyncio.sleep(current_try)

        if current_try == 2:
            req_channel = await refresh_channel_token_no_client(req_channel, db, api)

        if current_try > 2:
            req_channel = await refresh_channel_token_no_client(req_channel, db, api, force_refresh=True)

        sub_data, sub_error = await api.sub_check(req_channel['token'], req_channel['tw_id'], user_twitch_id)
        if sub_error is not None and (sub_error.startswith('401') or 'unauthorized' in sub_error.lower()):
            api.logger.error('Skip because of unauthorized')
            continue

        break

    return sub_data, sub_error


async def get_active_oauth_data(kb_user_id, db, api, force_refresh=False, sec_diff=30):
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

            # Resubscribe, err is thrown due to empty body
            try:
                await api.twitch.webhook_subscribe_subscribtion(user['tw_id'], resp['access_token'])
            except Exception as err:
                pass

            try:
                data = {"token": resp['access_token'], "tw_id": user['tw_id'], "scope": resp['scope']}
                await db.redis.publish_event(redis_key.get_token_update_topic(), data)
            except Exception as ex:
                print('Failed to publish redis data:' + str(ex))

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


async def get_active_app_token(api, forced=False)->str:
    if api.redis is None:
        raise Exception("Can not use get_active_app_token if redis is not enabled")

    token = None
    cache_key = redis_key.get_twitch_app_token()

    if not forced:
        token = await api.redis.get_value_by_key(cache_key)

    if token is None:
        print('App token was not found in cache, generating new one')
        api.logger.info('App token was not found in cache, generating new one')
        resp = await api.refresh_app_token()
        token = resp['access_token']
        expires_in = resp['expires_in']
        api.logger.info('Saving new generated token to cache')
        # Remove 1 day from expiration to avoid 401 errors during requests
        await api.redis.set_value_by_key(cache_key, token, expires_in - redis_key.ttl_day)

    return token
