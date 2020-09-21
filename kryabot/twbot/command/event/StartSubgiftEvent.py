from datetime import datetime

from twbot import ResponseAction
from twbot.command.AccessType import AccessType
from twbot.command.CommandBase import CommandBase
from twbot.processor.EventProcessor import EventProcessor


class StartSubgiftEvent(CommandBase):
    names = ['startsubgiftevent']
    access = AccessType.mod_package()

    async def process(self):
        try:
            key = self.get_word_list()
            if key is None:
                self.logger.info('User {} wanted to star event but keyword is missing!'.format(self.context.user.name))
                return

            await EventProcessor.get_instance().start_event(self.context, key, 0, 1)
        except Exception as e:
            self.logger.info(self.context)
            self.logger.exception(e)