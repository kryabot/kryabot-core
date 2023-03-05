from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import DateTime
from sqlalchemy.sql.functions import random, func
from sqlalchemy.orm import declarative_base
from utils.DaoUtils import DaoUtils
from sqlalchemy import select

Base = declarative_base()


class TwitchMessage(Base, DaoUtils):
    __tablename__ = "twitch_message"

    id = Column("twitch_message_id", Integer, primary_key=True)
    channel_id = Column(Integer, nullable=False)
    user_id = Column(Integer, nullable=False)
    message_id = Column(String, nullable=False)
    text = Column(String, nullable=False)
    sent_at = Column(DateTime, nullable=False)

    def __repr__(self):
        return f"TwitchMessage(twitch_message_id={self.id!r}, channel_id={self.channel_id!r}, user_id={self.user_id!r}, message_id={self.message_id!r} text={self.text!r}, sent_at={self.sent_at!r})"

    @staticmethod
    async def getAllMessagesByUserInChannel(channel_id: int, user_id: int):
        query = select(TwitchMessage.text, TwitchMessage.sent_at).where(TwitchMessage.channel_id == channel_id, TwitchMessage.user_id == user_id)

        return await DaoUtils.execute_all(query)

    @staticmethod
    async def getRandomUserMessageInChannel(channel_id: int, user_id: int):
        query = select(TwitchMessage).where(TwitchMessage.channel_id == channel_id, TwitchMessage.user_id == user_id).order_by(random()).limit(1)
        response = await DaoUtils.execute_first(query)

        return response[0] if response else None

    @staticmethod
    async def getCountOfUserMessagesInChannel(channel_id: int, user_id: int) -> int:
        query = select(func.count(TwitchMessage.message_id)).where(TwitchMessage.channel_id == channel_id, TwitchMessage.user_id == user_id)
        response = await DaoUtils.execute_first(query)

        return response[0] if response else 0

    @staticmethod
    async def getLatestUserMessageInChannel(channel_id: int, user_id: int):
        query = select(TwitchMessage).where(TwitchMessage.channel_id == channel_id, TwitchMessage.user_id == user_id).order_by(TwitchMessage.sent_at.desc()).limit(1)
        response = await DaoUtils.execute_first(query)

        return response[0] if response else None

