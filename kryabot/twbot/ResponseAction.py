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


class Response(Base):
    redis: RedisHelper

    def __init__(self, body, ws):
        self.body = body
        self.ws: WebsocketConnection = ws
        self.type: ResponseType = None
        self.me: User = None
        self.channel: Channel = None
        self.max_retries = 5

    async def process(self):
        raise NotImplemented

    async def get_channel(self)->[Channel, None]:
        tries = 0
        while tries < self.max_retries:
            try:
                return self.ws._channel_cache[self.body['channel']]['channel']
            except (KeyError, TypeError):
                await asyncio.sleep(tries / 2)
                tries += 1
                continue

    async def get_me(self)->[User, None]:
        try:
            return self.ws._channel_cache[self.body['channel']]['bot']
        except (KeyError, TypeError):
            return None

    async def can_process(self)->bool:
        if self.type == ResponseType.ACTION_JOIN:
            return True

        if not self.me:
            self.me = await self.get_me()

        return self.me and self.me.is_mod

    @staticmethod
    def build(**args) -> Dict:
        # This method used to generate response body which will be sent to queue.
        raise NotImplemented

    @classmethod
    async def send(cls, **args)->None:
        if cls.redis is None:
            raise Exception('Redis instance not set in ResponseAction class')

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


class ResponseBan(Response):
    async def process(self):
        target = self.body['user']
        reason = self.body['reason']
        await self.channel.ban(user=target, reason=reason)

    @staticmethod
    def build(channel_name: str, user: str, reason: str)->Dict:
        body = {
            "type": ResponseType.ACTION_BAN,
            "channel": channel_name,
            "user": user,
            "reason": reason,
        }
        return body

    @classmethod
    async def send(cls, channel_name: str, user: str, reason: str):
        await super().send(channel_name=channel_name, user=user, reason=reason)


class ResponseUnban(Response):
    async def process(self):
        target = self.body['user']
        await self.channel.unban(target)

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
        await self.channel.timeout(user=target, duration=int(duration), reason=reason)

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
        await self.channel.send('.emoteonly')

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
        await self.channel.send('.emoteonlyoff')

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
        if duration > 0:
            await self.channel.send('.slow {}'.format(duration))
        else:
            await self.channel.slow()

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
        await self.channel.slow_off()

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
        await self.channel.send('.subscribers')

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
        await self.channel.send('.subscribersoff')

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
        if duration > 0:
            await self.channel.send('.followers {}'.format(duration))
        else:
            await self.channel.send('.followers')

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
        await self.channel.send('.followersoff')

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
        await self.channel.send('/mods')

    @staticmethod
    def build(channel_name: str)->Dict:
        body = {
            "type": ResponseType.UPDATE_MOD_STA,
            "channel": channel_name,
        }
        return body

    @classmethod
    async def send(cls, channel_name: str):
        await super().send(channel_name=channel_name)


def get_class(action: ResponseType) -> [Response]:
    return {
        ResponseType.MESSAGE: ResponseMessage,
        ResponseType.ACTION_BAN: ResponseBan,
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

    def build(self, body)->Response:
        action = ResponseType(body['type'])
        class_type = get_class(action=action)
        obj = class_type(body, self.ws)
        obj.type = action
        return obj

    async def process(self, body)->None:
        resp = self.build(body)
        if resp is None:
            self.logger.warning('Failed to build resp for: {}'.format(body))
            return

        resp.me = await resp.get_me()
        resp.channel = await resp.get_channel()

        if await resp.can_process():
            await resp.process()
        else:
            self.logger.info('Skip due to missing permissions: {}'.format(body))
            update = ResponseUpdateModStatus(ws=self.ws, body=ResponseUpdateModStatus.build(resp.channel.name if resp.channel else body['channel']))
            await update.process()
