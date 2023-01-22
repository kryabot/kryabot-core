import asyncio
import logging
from typing import Dict

from object.Base import Base
from object.RedisHelper import RedisHelper
from twbot.ReponseType import ResponseType
from twitchio import Channel, User
from twitchio.websocket import WebsocketConnection
from utils import redis_key
from utils.json_parser import dict_to_json
from api.twitchv5.topics.Moderation import ChatSetting


class Response(Base):
    redis: RedisHelper
    _api = None

    def __init__(self, body, ws):
        self.body = body
        self.ws: WebsocketConnection = ws
        self.type: ResponseType = None
        self.me: User = None
        self.have_rights: bool = False
        self.channel: Channel = None
        self.max_retries = 5

    @property
    def api(self):
        # Add redis to api helper if it was initialized without redis
        if Response._api and not Response._api.redis:
            Response._api.redis = Response.redis

        return Response._api

    async def process(self):
        raise NotImplementedError

    async def get_channel(self) -> [Channel, None]:
        tries = 0
        while tries < self.max_retries:
            try:
                channel = self.ws._channel_cache[self.body['channel']]['channel']
                if channel.access_rights is None:
                    channel.access_rights, self.me._mod = await self.api.twitch.is_bot_mod(broadcaster_id=channel['id'])
                return channel
            except (KeyError, TypeError):
                await asyncio.sleep(tries / 2)
                tries += 1
                continue

    async def get_me(self) -> [User, None]:
        try:
            return self.ws._channel_cache[self.body['channel']]['bot']
        except (KeyError, TypeError):
            return None

    async def can_process(self) -> bool:
        if self.type == ResponseType.ACTION_JOIN:
            return True

        if not self.channel:
            self.channel = await self.get_channel()

        if not self.me:
            self.me = await self.get_me()

        return self.me and self.me.is_mod and self.channel.access_rights

    async def fetch_user_by_username(self, username: str):
        user = await self.api.twitch.get_users(usernames=[username])
        if not user or not user['data']:
            raise ValueError('Failed to find twitch user for username {}'.format(user))

        return user['data'][0]

    @staticmethod
    def build(**args) -> Dict:
        # This method used to generate response body which will be sent to queue.
        raise NotImplementedError

    @classmethod
    async def send(cls, **args) -> None:
        if cls.redis is None:
            raise ValueError('Redis instance not set in ResponseAction class')

        await cls.redis.push_list_to_right(redis_key.get_irc_response_queue(), dict_to_json(cls.build(**args)))


class ResponseMessage(Response):
    async def process(self):
        message = self.body['message']
        await self.channel.send(message)

    @staticmethod
    def build(channel_name: str, message: str)->Dict:
        body = {
            "type": ResponseType.MESSAGE,
            "channel": channel_name,
            "message": message,
        }
        return body

    @classmethod
    async def send(cls, channel_name: str, message: str):
        await super().send(channel_name=channel_name, message=message)


class ResponseUnban(Response):
    async def process(self):
        target = self.body['user']

        channel = await self.fetch_user_by_username(self.channel.name)
        user = await self.fetch_user_by_username(target)

        await self.api.twitch.unban_user(broadcaster_id=channel['id'], user_id=user['id'])

    @staticmethod
    def build(channel_name: str, user: str)->Dict:
        body = {
            "type": ResponseType.ACTION_UNBAN,
            "channel": channel_name,
            "user": user,
        }
        return body

    @classmethod
    async def send(cls, channel_name: str, user: str):
        await super().send(channel_name=channel_name, user=user)


class ResponseTimeout(Response):
    async def process(self):
        target = self.body['user']
        reason = self.body['reason'] or ''
        duration = self.body['duration'] or 600

        channel = await self.fetch_user_by_username(self.channel.name)
        user = await self.fetch_user_by_username(target)

        await self.api.twitch.ban_user(broadcaster_id=channel['id'], user_id=user['id'], duration=duration, reason=reason)

    @staticmethod
    def build(channel_name: str, user: str, duration: int, reason: str)->Dict:
        body = {
            "type": ResponseType.ACTION_TIMEOUT,
            "channel": channel_name,
            "user": user,
            "duration": duration,
            "reason": reason
        }
        return body

    @classmethod
    async def send(cls, channel_name: str, user: str, duration: int,  reason: str):
        await super().send(channel_name=channel_name, user=user, duration=duration, reason=reason)


class ResponseEmoteOnly(Response):
    async def process(self):
        channel = await self.fetch_user_by_username(self.channel.name)
        await self.api.twitch.patch_chat_settings(broadcaster_id=channel['id'], options={ChatSetting.EMOTE_MODE.value: True})

    @staticmethod
    def build(channel_name: str)->Dict:
        body = {
            "type": ResponseType.MODE_EMOTE,
            "channel": channel_name,
        }
        return body

    @classmethod
    async def send(cls, channel_name: str):
        await super().send(channel_name=channel_name)


class ResponseEmoteOnlyOff(Response):
    async def process(self):
        channel = await self.fetch_user_by_username(self.channel.name)
        await self.api.twitch.patch_chat_settings(broadcaster_id=channel['id'], options={ChatSetting.EMOTE_MODE.value: False})

    @staticmethod
    def build(channel_name: str)->Dict:
        body = {
            "type": ResponseType.MODE_EMOTE_OFF,
            "channel": channel_name,
        }
        return body

    @classmethod
    async def send(cls, channel_name: str):
        await super().send(channel_name=channel_name)


class ResponseSlow(Response):
    async def process(self):
        duration = int(self.body['duration'])
        channel = await self.fetch_user_by_username(self.channel.name)
        await self.api.twitch.patch_chat_settings(broadcaster_id=channel['id'], options={ChatSetting.SLOW_MODE.value: True, ChatSetting.SLOW_MODE_WAIT_TIME.value: duration})

    @staticmethod
    def build(channel_name: str, duration: int)->Dict:
        body = {
            "type": ResponseType.MODE_SLOW,
            "channel": channel_name,
            "duration": duration
        }
        return body

    @classmethod
    async def send(cls, channel_name: str, duration: int):
        await super().send(channel_name=channel_name, duration=duration)


class ResponseSlowOff(Response):
    async def process(self):
        channel = await self.fetch_user_by_username(self.channel.name)
        await self.api.twitch.patch_chat_settings(broadcaster_id=channel['id'], options={ChatSetting.SLOW_MODE.value: False})

    @staticmethod
    def build(channel_name: str)->Dict:
        body = {
            "type": ResponseType.MODE_SLOW_OFF,
            "channel": channel_name
        }
        return body

    @classmethod
    async def send(cls, channel_name: str):
        await super().send(channel_name=channel_name)


class ResponseSubOnly(Response):
    async def process(self):
        channel = await self.fetch_user_by_username(self.channel.name)
        await self.api.twitch.patch_chat_settings(broadcaster_id=channel['id'], options={ChatSetting.SUBSCRIBER_MODE.value: True})

    @staticmethod
    def build(channel_name: str)->Dict:
        body = {
            "type": ResponseType.MODE_SUB,
            "channel": channel_name,
        }
        return body

    @classmethod
    async def send(cls, channel_name: str):
        await super().send(channel_name=channel_name)


class ResponseSubOnlyOff(Response):
    async def process(self):
        channel = await self.fetch_user_by_username(self.channel.name)
        await self.api.twitch.patch_chat_settings(broadcaster_id=channel['id'], options={ChatSetting.SUBSCRIBER_MODE.value: False})

    @staticmethod
    def build(channel_name: str)->Dict:
        body = {
            "type": ResponseType.MODE_SUB_OFF,
            "channel": channel_name,
        }
        return body

    @classmethod
    async def send(cls, channel_name: str):
        await super().send(channel_name=channel_name)


class ResponseFollowOnly(Response):
    async def process(self):
        duration = int(self.body['duration'])
        channel = await self.fetch_user_by_username(self.channel.name)
        await self.api.twitch.patch_chat_settings(broadcaster_id=channel['id'],
                                                  options={ChatSetting.FOLLOWER_MODE.value: True, ChatSetting.FOLLOWER_MODE_DURATION.value: duration})

    @staticmethod
    def build(channel_name: str, duration: int)->Dict:
        body = {
            "type": ResponseType.MODE_FOLLOW,
            "channel": channel_name,
            "duration": duration
        }
        return body

    @classmethod
    async def send(cls, channel_name: str, duration: int):
        await super().send(channel_name=channel_name, duration=duration)


class ResponseFollowOnlyOff(Response):
    async def process(self):
        channel = await self.fetch_user_by_username(self.channel.name)
        await self.api.twitch.patch_chat_settings(broadcaster_id=channel['id'],
                                                  options={ChatSetting.FOLLOWER_MODE.value: False})

    @staticmethod
    def build(channel_name: str)->Dict:
        body = {
            "type": ResponseType.MODE_FOLLOW_OFF,
            "channel": channel_name,
        }
        return body

    @classmethod
    async def send(cls, channel_name: str):
        await super().send(channel_name=channel_name)


class ResponseChannelJoin(Response):
    async def process(self):
        channel_name = self.body['channel']
        await self.ws._join_channel(channel_name)

    @staticmethod
    def build(channel_name: str)->Dict:
        body = {
            "type": ResponseType.ACTION_JOIN,
            "channel": channel_name,
        }
        return body

    @classmethod
    async def send(cls, channel_name: str):
        await super().send(channel_name=channel_name)


class ResponseChannelLeave(Response):
    async def process(self):
        channel_name = self.body['channel']
        await self.ws.part_channels(channel_name)

    @staticmethod
    def build(channel_name: str)->Dict:
        body = {
            "type": ResponseType.ACTION_LEAVE,
            "channel": channel_name,
        }
        return body

    @classmethod
    async def send(cls, channel_name: str):
        await super().send(channel_name=channel_name)


class ResponseUpdateModStatus(Response):
    async def process(self):
        await self.can_process()

        channel = await self.fetch_user_by_username(self.channel.name)
        mod_status = self.body['status']

        if mod_status == 'refresh':
            self.channel.access_rights, self.me._mod = await self.api.twitch.is_bot_mod(broadcaster_id=channel['id'])
        elif mod_status == 'add':
            self.me._mod = True
        elif mod_status == 'remove':
            self.me._mod = False

    @staticmethod
    def build(channel_name: str, status: str = 'refresh')->Dict:
        body = {
            "type": ResponseType.UPDATE_MOD_STA,
            "channel": channel_name,
            "status": status,
        }
        return body

    @classmethod
    async def send(cls, channel_name: str, status: str = 'refresh'):
        await super().send(channel_name=channel_name, status=status)


def get_class(action: ResponseType) -> [Response]:
    return {
        ResponseType.MESSAGE: ResponseMessage,
        ResponseType.ACTION_UNBAN: ResponseUnban,
        ResponseType.ACTION_TIMEOUT: ResponseTimeout,
        ResponseType.ACTION_JOIN: ResponseChannelJoin,
        ResponseType.ACTION_LEAVE: ResponseChannelLeave,
        ResponseType.MODE_EMOTE: ResponseEmoteOnly,
        ResponseType.MODE_EMOTE_OFF: ResponseEmoteOnlyOff,
        ResponseType.MODE_FOLLOW: ResponseFollowOnly,
        ResponseType.MODE_FOLLOW_OFF: ResponseFollowOnlyOff,
        ResponseType.MODE_SLOW: ResponseSlow,
        ResponseType.MODE_SLOW_OFF: ResponseSlowOff,
        ResponseType.MODE_SUB: ResponseSubOnly,
        ResponseType.MODE_SUB_OFF: ResponseSubOnlyOff,
        ResponseType.UPDATE_MOD_STA: ResponseUpdateModStatus,
    }.get(action, Response)


class ResponseAction(Base):
    def __init__(self, ws, logger: logging):
        self.ws = ws
        self.logger: logging = logger

    def build(self, body) -> Response:
        action = ResponseType(body['type'])
        class_type = get_class(action=action)
        obj = class_type(body, self.ws)
        obj.type = action
        return obj

    async def process(self, body) -> None:
        resp = self.build(body)
        if resp is None:
            self.logger.warning('Failed to build resp for: {}'.format(body))
            return

        if await resp.can_process():
            await resp.process()
        else:
            self.logger.info('Skip due to missing permissions: {}'.format(body))
            update = ResponseUpdateModStatus(ws=self.ws, body=ResponseUpdateModStatus.build(resp.channel.name if resp.channel else body['channel']))
            await update.process()
