from __future__ import annotations

from datetime import datetime
from typing import Dict, List

from object.Base import Base
from twbot.command.AccessType import AccessType
from twbot.object.Channel import Channel
from twbot.object.ChannelCache import ChannelCache
from twbot.object.User import User


class MessageContext(Base):
    def __init__(self, data):
        self.channel: Channel = None
        self.user: User = None
        self.tags: Dict = None
        self.is_owner: bool = False
        self.is_mod: bool = False
        self.is_subscriber: bool = False
        self.is_turbo: bool = False
        self.is_admin: bool = False
        self.message: str = ''
        self.badge_info = None
        self.ts: datetime = None
        self.rights: List[AccessType] = [AccessType.CHANNEL_USER]

        if data is not None:
            self.parse(data)

        self.set_rights()

    async def reply(self, message: str)->None:
        await self.channel.reply(message)

    async def timeout(self, user: str, duration: int, reason: str)->None:
        await self.channel.timeout(user, duration, reason)

    async def ban(self, user: str, reason: str)->None:
        await self.channel.ban(user, reason)

    def set_user_db_info(self, db_info)->None:
        self.user.set_db_info(db_info)

    def parse(self, data)->None:
        self.channel = ChannelCache.get(data["channel"])
        self.user = User(data["sender"], data["sender_id"], data["display_name"])
        self.tags = data["tags"]
        self.message = data["message"]
        self.ts = data["ts"]
        self.badge_info = self.tags.get("badge-info", None)
        self.is_mod = self.get_mod_status()
        self.is_subscriber = self.get_sub_status()
        self.is_turbo = self.get_turbo_status()
        self.is_owner = self.channel.channel_name.lower() == self.user.name.lower()

    def get_bits(self)->int:
        try:
            return self.tags and int(self.tags.get("bits")) > 0
        except Exception as ex:
            return 0

    def has_bits(self)->bool:
        return self.get_bits() > 0

    def get_sub_months(self)->int:
        if self.badge_info:
            try:
                parts = self.badge_info.split('/')
                if parts[0] in ['subscriber', 'founder']:
                    return int(parts[1])
            except:
                pass

        return 0

    def get_mod_status(self)->bool:
        if self.tags:
            return bool(self.tags.get('mod', 0))
        return False

    def get_sub_status(self)->bool:
        if self.tags:
            return bool(self.tags.get('subscriber', 0))
        return False

    def get_turbo_status(self)->bool:
        if self.tags:
            return bool(self.tags.get('turbo', 0))
        return False

    def set_rights(self):
        if self.is_owner:
            self.rights.append(AccessType.CHANNEL_OWNER)

        if self.is_mod:
            self.rights.append(AccessType.CHANNEL_MOD)

        if self.is_subscriber:
            self.rights.append(AccessType.CHANNEL_SUB)

        if self.is_admin:
            self.rights.append(AccessType.BOT_ADMIN)
