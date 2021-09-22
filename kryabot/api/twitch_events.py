from enum import Enum

from aiohttp import ClientResponseError

from api.core import Core
from api.twitch import app_auth
from exceptions.twitch import ExpiredAuthToken
from object.Base import Base
from utils.twitch import get_active_app_token


class EventSubType(Enum):
    CHANNEL_UPDATE = 'channel.update'
    CHANNEL_FOLLOW = 'channel.follow'
    CHANNEL_SUBSCRIBE = 'channel.subscribe'
    CHANNEL_SUBSCRIBE_END = 'channel.subscription.end'
    CHANNEL_SUBSCRIBE_GIFT = 'channel.subscription.gift'
    CHANNEL_SUBSCRIBE_MESSAGE = 'channel.subscription.message'
    CHANNEL_CHEER = 'channel.cheer'
    CHANNEL_RAID = 'channel.raid'
    CHANNEL_BAN = 'channel.ban'
    CHANNEL_UNBAN = 'channel.unban'
    CHANNEL_MOD_ADD = '	channel.moderator.add'
    CHANNEL_MOD_REMOVE = 'channel.moderator.remove'
    CHANNEL_POINTS_UPDATE = 'channel.channel_points_custom_reward.update'
    CHANNEL_POINTS_REMOVE = 'channel.channel_points_custom_reward.remove'
    CHANNEL_POINTS_REDEMPTION_UPDATE = 'channel.channel_points_custom_reward_redemption.update'
    CHANNEL_POINTS_REDEMPTION_NEW = 'channel.channel_points_custom_reward_redemption.add'
    CHANNEL_POLL_BEGIN = 'channel.poll.begin'
    CHANNEL_POLL_PROCESS = 'channel.poll.progress'
    CHANNEL_POLL_END = 'channel.poll.end'
    CHANNEL_PREDICTION_BEGIN = 'channel.prediction.begin'
    CHANNEL_PREDICTION_PROCESS = '	channel.prediction.progress'
    CHANNEL_PREDICTION_LOCK = 'channel.prediction.lock'
    CHANNEL_PREDICTION_END = 'channel.prediction.end'
    CHANNEL_GOAL_BEGIN = 'channel.goal.begin'
    CHANNEL_GOAL_PROGRESS = 'channel.goal.progress'
    CHANNEL_GOAL_END = 'channel.goal.end'
    CHANNEL_HYPE_TRAIN_BEGIN = 'channel.hype_train.begin'
    CHANNEL_HYPE_TRAIN_PROGRESS = 'channel.hype_train.progress'
    CHANNEL_HYPE_TRAIN_END = 'channel.hype_train.end'
    STREAM_ONLINE = 'stream.online'
    STREAM_OFFLINE = 'stream.offline'
    AUTH_GRANTED = 'user.authorization.grant'
    AUTH_REVOKED = 'user.authorization.revoke'
    USER_UPDATE = 'user.update'


class EventSubStatus(Enum):
    ENABLED = 'enabled'
    PENDING = 'webhook_callback_verification_pending'
    FAILED = 'webhook_callback_verification_failed'
    FAILURES = 'notification_failures_exceeded'
    AUTH_REVOKED = 'authorization_revoked'
    USER_REMOVED = 'user_removed'


class Event(Base):
    pass


class TwitchEvents(Core):
    def __init__(self, redis, cfg=None):
        super().__init__(cfg=cfg)
        self.client_id = self.cfg.getTwitchConfig()['API_KEY']
        self.client_secret = self.cfg.getTwitchConfig()['SECRET']
        self.events_url = 'https://api.twitch.tv/helix/eventsub/subscriptions'
        self.callback = 'https://api2.krya.dev/public/callback/twitch_events'
        self.redis = redis
        self.webhook_secret = 'supermegasecret'

    async def get_headers(self, oauth_token=None):
        if oauth_token:
            raise ValueError('Oauth token not supported in EventSubs, must use app token.')

        headers = {
            'Accept': 'application/json',
            'Client-ID': self.client_id
        }

        #bearer_token = await get_active_app_token(self)
        bearer_token = 'lblhw91mu74cc1cj1ltauhb9fyriin'
        headers['Authorization'] = 'Bearer {}'.format(bearer_token)

        return headers

    async def is_success(self, response):
        try:
            return await super().is_success(response)
        except ClientResponseError as e:
            if e.status == 401:
                raise ExpiredAuthToken(e)
            else:
                raise e

    async def create_many(self, broadcaster_id: str, topics: [EventSubType]):
        response = []
        for topic in topics:
            resp = await self.create(broadcaster_id, topic)
            response.append(resp)

        return response

    @app_auth()
    async def create(self, broadcaster_id: str, topic: EventSubType, version: int=1):
        if not topic:
            raise ValueError('Must provide topic value!')

        if not broadcaster_id:
            raise ValueError('Must provide broadcaster_id value!')

        body = {
            'type': topic.value,
            'version': version,
            'condition': {'broadcaster_user_id': str(broadcaster_id)},
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
            if response:
                response['data'] += page['data']
            else:
                response = page

        return response

    async def handle_event(self, event):
        self.logger.info(event)


        # db.redis.push_list_to_right(redis_key.get_streams_data(), request.body)