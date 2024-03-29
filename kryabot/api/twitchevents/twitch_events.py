import asyncio
from datetime import datetime
from typing import Dict

from aiohttp import ClientResponseError

from api.core import Core
from api.twitchevents.EventSubStatus import EventSubStatus
from api.twitchevents.EventSubType import EventSubType
from api.twitchv5.exception import ExpiredAuthToken
from object.RedisHelper import RedisHelper
from twbot import ResponseAction
from utils.constants import BOT_TWITCH_ID
from utils.twitch import app_auth
from object.Base import Base
from object.Database import Database
from utils.array import get_first
from utils.json_parser import dict_to_json
from utils.twitch import get_active_app_token
import utils.redis_key as redis_key


class TwitchEvents(Core):
    def __init__(self):
        super().__init__()
        self.client_id = self.cfg.getTwitchConfig()['API_KEY']
        self.client_secret = self.cfg.getTwitchConfig()['SECRET']
        self.events_url = 'https://api.twitch.tv/helix/eventsub/subscriptions'
        self.callback = 'https://api2.krya.dev/public/callback/twitch_events'
        self.redis = RedisHelper.get_instance()
        self.webhook_secret = 'supermegasecret'
        self.db = Database.get_instance()

    async def get_headers(self, oauth_token=None):
        if oauth_token:
            raise ValueError('Oauth token not supported in EventSubs, must use app token.')

        headers = {
            'Accept': 'application/json',
            'Client-ID': self.client_id
        }

        bearer_token = await get_active_app_token(self)
        headers['Authorization'] = 'Bearer {}'.format(bearer_token)

        return headers

    async def is_success(self, response):
        try:
            return await super().is_success(response)
        except ClientResponseError as e:
            if e.status == 401:
                body = await response.json()
                raise ExpiredAuthToken(body) from e
            else:
                raise e

    async def create_many(self, broadcaster_id: str, topics: [EventSubType]):
        response = []
        error = []

        for topic in topics:
            try:
                resp = await self.create(topic=topic, broadcaster_id=broadcaster_id)
                response.append(resp['data'][0])
            except Exception as ex:
                error.append(ex)

        return response, error

    async def create_for_client(self, topic: EventSubType):
        return await self.create(topic=topic, client_id=self.client_id)

    @app_auth()
    async def create(self, topic: EventSubType,
                     broadcaster_id: str=None,
                     to_broadcaster_user_id: str=None,
                     from_broadcaster_user_id: str=None,
                     client_id: str=None,
                     version: int=1):
        if not topic:
            raise ValueError('Must provide topic value!')

        condition = {}
        if broadcaster_id:
            condition['broadcaster_user_id'] = str(broadcaster_id)
        if to_broadcaster_user_id:
            condition['to_broadcaster_user_id'] = str(to_broadcaster_user_id)
        if from_broadcaster_user_id:
            condition['from_broadcaster_user_id'] = str(from_broadcaster_user_id)
        if client_id:
            condition['client_id'] = str(client_id)

        if not condition or condition == {}:
            raise ValueError('Failed to build condition data')

        body = {
            'type': topic.value,
            'version': version,
            'condition': condition,
            'transport': {
                'method': 'webhook',
                'callback': self.callback,
                'secret': self.webhook_secret
            }
        }

        try:
            return await self.make_post_request(self.events_url, body=body)
        except ClientResponseError as responseException:
            if responseException.status == 409 and responseException.message == 'Conflict':
                existing_subs = await self.get_all(topic=topic)
                event = next(filter(lambda row: int(broadcaster_id) == int(row['condition']['broadcaster_user_id']), existing_subs['data']), None)
                if event is None:
                    # Something wrong, unexpected case, maybe race condition
                    self.logger.info(existing_subs)
                    self.logger.error('Event sub create received conflict and also failed to find existing subscription for user {} topic {}'.format(broadcaster_id, topic.value))
                    raise responseException
                if event['status'] == EventSubStatus.ENABLED.value:
                    self.logger.info('Received create event for user {} topic {}, but already have active subscription, ignoring exception'.format(broadcaster_id, topic.value))
                    return {'data': [event],
                            'max_total_cost': existing_subs['max_total_cost'],
                            'total_cost': existing_subs['total_cost']
                            }
                else:
                    self.logger.error('Conflict with existing event: {}'.format(event))
                    raise responseException

    @app_auth()
    async def delete(self, message_id: str):
        params = [('id', message_id)]
        return await self.make_delete_request_data(self.events_url, params=params)

    @app_auth()
    async def delete_all(self, status: EventSubStatus=None, topic: EventSubType=None):
        current = await self.get_all(status, topic)

        self.logger.info('Deleting {} subscriptions for {} topic and status {}'.format(
            current['total'],
            topic.value if topic else 'any',
            status.value if status else 'any'
        ))

        # TODO: async gather for parallel?
        for item in current['data']:
            await self.delete(item['id'])

    @app_auth()
    async def get(self, status: EventSubStatus=None, topic: EventSubType=None, after: str=None):
        params = []
        '''
        Use the status and type query parameters to filter the list of subscriptions that are returned. 
        You may specify only one filter query parameter (i.e., specify either the status or type parameter, but not both). 
        The request fails if you specify both filter parameters.
        
        https://dev.twitch.tv/docs/api/reference#get-eventsub-subscriptions
        '''

        if status and topic:
            raise ValueError("Cannot use status and topic at same time!")
        if status:
            params.append(('status', status))
        if topic:
            params.append(('type', topic.value))
        if after:
            params.append(('after', after))

        return await self.make_get_request(self.events_url, params=params)

    async def get_all(self, status: EventSubStatus=None, topic: EventSubType=None):
        first = True
        after = None
        response = None

        while after is not None or first:
            first = False
            page = await self.get(status, topic, after)
            if page and 'cursor' in page['pagination']:
                after = page['pagination']['cursor']
            else:
                after = None
            if response:
                response['data'] += page['data']
            else:
                response = page

        return response

    async def handle_event(self, event):
        self.logger.info(event)

        status = EventSubStatus(event['subscription']['status'])
        if status == EventSubStatus.ENABLED:
            await self.handle_active_event(event)
        elif status == EventSubStatus.AUTH_REVOKED:
            await self.handle_revoked(event)
        else:
            self.logger.info('Unhandled event status: {}'.format(status))
        # TODO: handle other statuses

    async def handle_active_event(self, event):
        topic = EventSubType(event['subscription']['type'])

        converted_event = dict_to_json(event)
        if topic.eq(EventSubType.STREAM_ONLINE) or topic.eq(EventSubType.STREAM_OFFLINE):
            await self.redis.push_list_to_right(redis_key.get_streams_data(), converted_event)
        elif topic.eq(EventSubType.CHANNEL_UPDATE):
            await self.redis.push_list_to_right(redis_key.get_streams_data(), converted_event)
            broadcaster_id = int(event['subscription']['condition']['broadcaster_user_id'])
            await self.redis.set_parsed_value_by_key(redis_key.get_twitch_channel_update(broadcaster_id), event['event'], expire=redis_key.ttl_week)
        elif topic.eq(EventSubType.CHANNEL_SUBSCRIBE):
            await self.handle_subscribe('subscriptions.subscribe', event['event'])
        elif topic.eq(EventSubType.CHANNEL_SUBSCRIBE_END):
            await self.handle_subscribe('subscriptions.unsubscribe', event['event'])
        elif topic.eq(EventSubType.CHANNEL_SUBSCRIBE_MESSAGE):
            await self.handle_subscribe('subscriptions.notification', event['event'])
        elif topic.eq(EventSubType.CHANNEL_POINTS_REDEMPTION_NEW):
            await self.redis.publish_event(redis_key.get_pubsub_topic(), event)
        elif topic.eq(EventSubType.AUTH_GRANTED):
            await self.handle_auth_granted(event)
        elif topic.eq(EventSubType.CHANNEL_MOD_REMOVE) or topic.eq(EventSubType.CHANNEL_MOD_ADD):
            await self.handle_mod_status_change(topic, event)
        else:
            self.logger.info('Unhandled type {}'.format(topic))

    async def handle_subscribe(self, event_type, data):
        user_id = int(data['user_id'])
        broadcaster_id = int(data['broadcaster_user_id'])

        user = await get_first(await self.db.getUserRecordByTwitchId(user_id))
        if user is None:
            await self.db.createUserRecord(user_id, data['user_login'], data['user_name'])
            await asyncio.sleep(1)
            user = await get_first(await self.db.getUserRecordByTwitchId(user_id, skip_cache=True))

        if user is None:
            self.logger.error('Failed to find user record for event: {}'.format(data))
            return

        channel = await get_first(await self.db.get_channel_by_twitch_id(broadcaster_id))
        if channel is None:
            self.logger.error('Failed to find channel record for event: {}'.format(data))
            # TODO: Send event removal to Twitch?
            return

        try:
            message = data['message']['text']
        except KeyError:
            message = ''

        try:
            gifted = bool(data['is_gift'])
        except KeyError:
            gifted = False

        try:
            tier = data['tier']
        except KeyError:
            tier = ''

        await self.db.saveTwitchSubEvent(channel['channel_id'], user['user_id'], '', event_type, datetime.utcnow(), gifted, tier, message)

    async def handle_unsubscribe(self, event):
        unsubscribed_user = await get_first(await self.db.getLinkageDataByTwitchId(event['user_id']))
        if not unsubscribed_user:
            # Not verified user
            return

        broadcaster = await get_first(await self.db.getUserRecordByTwitchId(event['broadcaster_user_id']))
        if not broadcaster:
            # streamer does not exist as user. It must exist when subchat exists.
            return

        subchat = await get_first(await self.db.getSubchatByUserId(broadcaster['user_id']))
        if not subchat:
            # streamer has no subchat
            return

        if subchat['kick_mode'] != 'ONLINE':
            # we interested only in online mode
            return

        special_rights = await self.db.get_all_tg_chat_special_rights(subchat['channel_id'])
        for right in special_rights:
            if right['user_id'] == unsubscribed_user['user_id'] and right['right_type'] == 'WHITELIST':
                self.logger.info('Skipping kick for Twitch user {} from {} becuse user is whitelisted.'.format(event['user_id'], event['broadcaster_user_id']))
                return

        request = {"task": "kick",
                   "tg_chat_id": subchat['tg_chat_id'],
                   "tg_user_id": unsubscribed_user['tg_id'],
                   "reason": "unsubscribe"}

        await self.redis.push_list_to_right(redis_key.get_tg_bot_requests(), dict_to_json(request))

    async def handle_revoked(self, data):
        broadcaster_id = int(data['subscription']['condition']['broadcaster_user_id'])
        channel_name: str = data['event']['user_login']
        self.logger.info('[{}] Revoked auth topic {}'.format(broadcaster_id, data['subscription']['type']))

        try:
            await self.delete(message_id=data['subscription']['id'])
        except Exception as ex:
            self.logger.exception(ex)

        user = await get_first(await self.db.getUserRecordByTwitchId(broadcaster_id))
        if user is None:
            self.logger.error('[{}] Failed to find user record'.format(broadcaster_id))
            return

        chat = await get_first(await self.db.getSubchatByUserId(user['user_id']))
        if chat is None:
            # Possible case, not an error
            self.logger.info('[{}] Failed to find chat'.format(broadcaster_id))
            return

        if chat['auth_status'] != 0:
            await self.db.updateSubchatAuthStatus(chat['channel_subchat_id'], 0)
            # Refresh cache
            await self.db.get_auth_subchat(chat['tg_chat_id'], True)

        await ResponseAction.ResponseUpdateModStatus.send(channel_name=channel_name)

    async def handle_auth_granted(self, data):
        broadcaster_id: int = int(data['event']['user_id'])
        channel_name: str = data['event']['user_login']

        user = await get_first(await self.db.getUserRecordByTwitchId(broadcaster_id))
        if user is None:
            self.logger.error('[{}] Failed to find user record'.format(broadcaster_id))
            return

        chat = await get_first(await self.db.getSubchatByUserId(user['user_id']))
        if chat is None:
            # Possible case, not an error
            self.logger.info('[{}] Failed to find chat'.format(broadcaster_id))
            return

        if chat['auth_status'] != 1:
            await self.db.updateSubchatAuthStatus(chat['channel_subchat_id'], 1)

        # Refresh cache
        await self.db.get_auth_subchat(chat['tg_chat_id'], True)
        await ResponseAction.ResponseUpdateModStatus.send(channel_name=channel_name)

    async def handle_mod_status_change(self, topic: EventSubType, data: Dict):
        try:
            user_id: int = data['event']['user_id']
            channel_name: str = data['event']['broadcaster_user_login']
        except IndexError as err:
            self.logger.exception(err)
            return

        if user_id == BOT_TWITCH_ID:
            await ResponseAction.ResponseUpdateModStatus.send(channel_name=channel_name, status='add' if topic.eq(EventSubType.CHANNEL_MOD_ADD) else 'remove')
