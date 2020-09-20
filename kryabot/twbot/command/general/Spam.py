from twbot.command.AccessType import AccessType
from twbot.command.CommandBase import CommandBase


class Spam(CommandBase):
    names = ['spam']
    access = AccessType.mod_package()

    def __init__(self, context):
        super().__init__(context)

    async def process(self):
        try:
            async def get_word_count(list, idx):
                try:
                    return int(list[idx])
                except:
                    return 0

            default_message_count = 10
            max_count = 20
            wlist = self.context.message.split()

            try:
                count = await get_word_count(wlist, 1)
                if count > 0:
                    del wlist[1]

                if count is None or count == 0 or count > max_count:
                    count = default_message_count

                del wlist[0]
                spam_text = ' '.join(wlist)

                if len(spam_text) > 0:
                    for x in range(count):
                        await self.context.reply(spam_text)
            except Exception as e:

                self.logger.exception(e)
                self.logger.error('global_spam_command: %s', str(e))
                return
        except Exception as e:
            self.logger.info(self.context)
            self.logger.exception(e)
