from twbot import ResponseAction
from twbot.command.AccessType import AccessType
from twbot.command.CommandBase import CommandBase
from utils.array import get_first


class TelegramInvite(CommandBase):
    names = ['tginvite']
    access = AccessType.mod_package()

    def __init__(self, context):
        super().__init__(context)

    async def process(self):
        try:
            tg_group = await self.db.getTgChatIdByChannelId(self.context.channel.channel_id)
            if tg_group is None or len(tg_group) == 0:
                await ResponseAction.ResponseMessage.send(self.context.channel.name, '{} this Twitch channel do not have linked Telegram group.'.format(self.context.user.name))
                return

            try:
                target_nick = self.context.message.split()[1]
                if target_nick.startswith('@'):
                    target_nick = target_nick[1:]
            except Exception as ex:
                await ResponseAction.ResponseMessage.send(self.context.channel.name, '{} missing twitch nickname as input.'.format(self.context.user.name))
                return

            self.logger.info('User {} adding telegram vip to {}'.format(self.context.user.name, target_nick))

            try:
                twitch_user_by_name = await self.api.twitch.get_user_by_name(target_nick)
                author_twitch_id = twitch_user_by_name['users'][0]['_id']
            except Exception as ex:
                await ResponseAction.ResponseMessage.send(self.context.channel.name, '{} i could not find user by your provided nickname ({})'.format(self.context.user.name, target_nick))
                return

            target_db_user = await get_first(await self.db.getUserRecordByTwitchId(author_twitch_id))
            if target_db_user is None:
                await ResponseAction.ResponseMessage.send(self.context.channel.name, '{} such user does not exists in my head ({})'.format(self.context.user.name, target_nick))
                return

            check_invite = await self.db.getTgInvite(self.context.channel.channel_id, target_db_user['user_id'])
            if len(check_invite) > 0:
                await ResponseAction.ResponseMessage.send(self.context.channel.name, '{} user {} already has active invitation!'.format(self.context.user.name, target_nick))
                return

            check_rights = await self.db.getUserRightsInChannel(self.context.channel.channel_id, target_db_user['user_id'])
            if check_rights is not None:
                for right in check_rights:
                    if right['right_type'] == 'WHITELIST':
                        await ResponseAction.ResponseMessage.send(self.context.channel.name, '{} user {} can join without invite because already has telegram vip right!'.format(self.context.user.name, target_nick))
                        return
                    if right['right_type'] == 'BLACKLIST':
                        await ResponseAction.ResponseMessage.send(self.context.channel.name, '{} user {} cannot be invited because user is banned (ban right in telegram)!'.format(self.context.user.name, target_nick))
                        return

            await self.db.saveTgInvite(self.context.channel.channel_id, target_db_user['user_id'], self.context.user.db_info['user_id'])

            await self.context.reply('{} created invitation for user {}! User now can join Telegram group via invite link https://tg.krya.dev/{}'.format(self.context.user.name, target_nick, self.context.channel.channel_name))
        except Exception as e:
            self.logger.info(self.context)
            self.logger.exception(e)
