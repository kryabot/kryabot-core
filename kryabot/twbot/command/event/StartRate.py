from twbot.command.AccessType import AccessType
from twbot.command.CommandBase import CommandBase
from twbot.processor.EventProcessor import EventProcessor


class StartRate(CommandBase):
    names = ['startrate']
    access = AccessType.mod_package()

    def __init__(self, context):
        super().__init__(context)

    async def process(self):
        try:
            await EventProcessor.get_instance().start_rate_event(irc_data=self.context, runtime=0)
        except Exception as e:
            self.logger.info(self.context)
            self.logger.exception(e)
