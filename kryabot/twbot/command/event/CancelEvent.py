from twbot.command.AccessType import AccessType
from twbot.command.CommandBase import CommandBase
from twbot.processor.EventProcessor import EventProcessor


class CancelEvent(CommandBase):
    names = ['cancelevent']
    access = AccessType.mod_package()

    async def process(self):
        try:
            await EventProcessor.get_instance().cancel_event(self.context)
        except Exception as e:
            self.logger.info(self.context)
            self.logger.exception(e)
