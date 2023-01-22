import logging
from typing import List

from object.ApiHelper import ApiHelper
from object.Base import Base
from object.Database import Database
from twbot.command.AccessType import AccessType
from twbot.object.MessageContext import MessageContext


class CommandBase(Base):
    names: List[str] = []
    access: List[AccessType] = []

    database_instance: Database
    api_instance: ApiHelper
    logger_instance: logging

    def __init__(self, context: MessageContext):
        self.context: MessageContext = context

    async def process(self):
        raise NotImplementedError

    @property
    def db(self) -> Database:
        if CommandBase.database_instance is None:
            raise ValueError('CommandBase.database_instance is not initiated!')

        return CommandBase.database_instance

    @property
    def api(self) -> ApiHelper:
        if CommandBase.api_instance is None:
            raise ValueError('CommandBase.api_instance is not initiated!')

        return CommandBase.api_instance

    @property
    def logger(self) -> logging:
        if CommandBase.logger_instance is None:
            raise ValueError('CommandBase.logger_instance is not initiated!')

        return CommandBase.logger_instance

    def get_word_list(self):
        content = self.context.message
        try:
            word_list = content.split()
            if len(word_list) > 1:
                del word_list[0]
                return ' '.join(word_list)
            elif len(word_list) == 1:
                return word_list[1]
            else:
                return None
        except IndexError:
            return None
