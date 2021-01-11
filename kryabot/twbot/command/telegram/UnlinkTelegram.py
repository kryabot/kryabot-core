from datetime import datetime

from twbot import ResponseAction
from twbot.command.AccessType import AccessType
from twbot.command.CommandBase import CommandBase


class UnlinkTelegram(CommandBase):
    names = ['unlinktelegram']
    access = [AccessType.CHANNEL_USER]

    def __init__(self, context):
        super().__init__(context)

    async def process(self):
        try:
            if self.context.user.twitch_id is None or self.context.user.twitch_id == 0:
                await ResponseAction.ResponseMessage.send(self.context.channel.name, '{} currently i am not feeling well, please try bit later.'.format(self.context.user.display_name))
                return

            linkage_data = await self.db.getLinkageDataByTwitchId(self.context.user.twitch_id)
            if linkage_data is None or len(linkage_data) == 0 or linkage_data[0]['response_id'] is None or linkage_data[0]['response_time'] is None:
                await ResponseAction.ResponseMessage.send(self.context.channel.name, '{} you do not have active telegram link!'.format(self.context.user.display_name))
                return

            day_limit = 30
            diff = datetime.now() - linkage_data[0]['response_time']
            if diff.days < day_limit:
                await ResponseAction.ResponseMessage.send(self.context.channel.name, '{} sorry, but can not unlink telegram account, yet! You can unlink only after {} day(s)'.format(self.context.user.display_name, day_limit - diff.days))
                return

            await self.db.deleteTelegramLink(linkage_data[0]['user_id'])
            await self.api.guardbot.notify_tg_unlink(linkage_data[0]['user_id'], self.context.user.twitch_id, linkage_data[0]['tg_id'])
            await ResponseAction.ResponseMessage.send(self.context.channel.name, '{} successfully unlinked!'.format(self.context.user.display_name))
        except Exception as e:
            self.logger.info(self.context.stringify())
            self.logger.exception(e)
