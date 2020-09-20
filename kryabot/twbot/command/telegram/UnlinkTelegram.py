from datetime import datetime

from twbot import ResponseAction
from twbot.command.AccessType import AccessType
from twbot.command.CommandBase import CommandBase


class UnlinkTelegram(CommandBase):
    names = ['unlinktelegram']
    access = [AccessType.CHANNEL_ANY]

    def __init__(self, channel, data):
        super().__init__(channel, data)

    async def process(self):
        try:
            if ctx.author.id is None or ctx.author.id == 0:
                await ResponseAction.ResponseMessage.send(self.channel.name, '{} currently i am not feeling well, please try bit later.'.format(ctx.author.name))
                return

            linkage_data = await self.db.getLinkageDataByTwitchId(ctx.author.id)
            if linkage_data is None or len(linkage_data) == 0 or linkage_data[0]['response_id'] is None or linkage_data[0]['response_time'] is None:
                await ResponseAction.ResponseMessage.send(self.channel.name, '{} you do not have active telegram link!'.format(ctx.author.name))
                return

            day_limit = 30
            diff = datetime.now() - linkage_data[0]['response_time']
            if diff.days < day_limit:
                await ResponseAction.ResponseMessage.send(self.channel.name, '{} sorry, but can not unlink telegram account, yet! You can unlink only after {} day(s)'.format(ctx.author.name, day_limit - diff.days))
                return

            await self.db.deleteTelegramLink(linkage_data[0]['user_id'])
            await self.api.guardbot.notify_tg_unlink(linkage_data[0]['user_id'], ctx.author.id, linkage_data[0]['tg_id'])
            await ResponseAction.ResponseMessage.send(self.channel.name, '{} successfully unlinked!'.format(ctx.author.name))
        except Exception as e:
            self.logger.info(self.data)
            self.logger.exception(e)
