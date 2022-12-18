from datetime import datetime

from tgbot.commands.common.user_data import unlink_user
from twbot import ResponseAction
from twbot.command.AccessType import AccessType
from twbot.command.CommandBase import CommandBase


class UnlinkTelegram(CommandBase):
    names = ['unlinktelegram', 'kbunlink']
    access = [AccessType.CHANNEL_USER]

    def __init__(self, context):
        super().__init__(context)

    async def process(self):
        try:
            if self.context.user.twitch_id is None or self.context.user.twitch_id == 0:
                await ResponseAction.ResponseMessage.send(self.context.channel.name, '{} currently i am not feeling well, please try bit later.'.format(self.context.user.display_name))
                return

            unlink_result = await unlink_user(self.db, self.api, self.context.user.twitch_id)
            if unlink_result['error'] == 'NOT_LINKED':
                await ResponseAction.ResponseMessage.send(self.context.channel.name, '{} you do not have active telegram link!'.format(self.context.user.display_name))
                return

            if unlink_result['error'] == 'UNLINK_TOO_EARLY':
                await ResponseAction.ResponseMessage.send(self.context.channel.name, '{} sorry, but can not unlink telegram account, yet! You can unlink only after {} day(s)'.format(self.context.user.display_name, unlink_result['days']))
                return

            if unlink_result['unlinked']:
                await ResponseAction.ResponseMessage.send(self.context.channel.name, '{} successfully unlinked!'.format(self.context.user.display_name))
            else:
                await ResponseAction.ResponseMessage.send(self.context.channel.name, '{} failed to unlinked, try later!'.format(self.context.user.display_name))
        except Exception as e:
            self.logger.info(self.context.stringify())
            self.logger.exception(e)
