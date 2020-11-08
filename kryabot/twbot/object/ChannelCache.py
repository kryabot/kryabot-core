from __future__ import annotations
from typing import Dict, Union

from object.Base import Base
from twbot.object.Channel import Channel


class ChannelCache(Base):
    instance = None

    def __init__(self):
        self.channels: Dict(str, Channel) = {}

    @staticmethod
    def get_instance()->ChannelCache:
        if ChannelCache.instance is None:
            ChannelCache.instance = ChannelCache()

        return ChannelCache.instance

    @staticmethod
    def get(channel_name: str)->Union[Channel, None]:
        try:
            return ChannelCache.get_instance().channels[str(channel_name).lower()]
        except KeyError:
            return None

    @staticmethod
    def get_by_twitch_id(twitch_id: int)->Channel:
        for channel_key in ChannelCache.get_all().keys():
            if ChannelCache.get(channel_key).tw_id == twitch_id:
                return ChannelCache.get(channel_key)

    @staticmethod
    def get_by_channel_id(channel_id: int)->Channel:
        for channel_key in ChannelCache.get_all().keys():
            if ChannelCache.get(channel_key).channel_id == channel_id:
                return ChannelCache.get(channel_key)

    @staticmethod
    def get_by_kb_user_id(kb_user_id: int)->Channel:
        for channel_key in ChannelCache.get_all().keys():
            if ChannelCache.get(channel_key).user_id == kb_user_id:
                return ChannelCache.get(channel_key)

    @staticmethod
    def add(channel: Channel):
        ChannelCache.get_instance().channels[str(channel.channel_name).lower()] = channel

    @staticmethod
    def get_all():
        return ChannelCache.get_instance().channels
