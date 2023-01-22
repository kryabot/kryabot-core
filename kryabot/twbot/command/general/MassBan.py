import asyncio

from twbot.command.AccessType import AccessType
from twbot.command.CommandBase import CommandBase


class MassBan(CommandBase):
    names = ['mban']
    access = AccessType.mod_package()

    def __init__(self, context):
        super().__init__(context)

    async def process(self):
        try:
            search_text = self.get_word_list()
            if len(search_text) < 4:
                await self.context.reply('Search text is too short! Must be longer than 4 characters')
                return

            vips = await self.api.twitch.get_vips(self.context.channel.tw_id)
            mods = await self.api.twitch.get_moderators(self.context.channel.tw_id)

            search_text = '%{}%'.format(search_text)
            self.logger.info('Searching messages to ban like {}'.format(search_text))
            messages = await self.db.searchTwitchMessages(self.context.channel.channel_id, search_text)
            self.logger.info('Received {} users to ban'.format(len(messages)))
            if messages is None or len(messages) == 0:
                await self.context.reply('{} no users found for mass ban!'.format(self.context.user.name))
                return
            else:
                await self.context.reply('{} starting to ban {} users! SirMad '.format(self.context.user.name, len(messages)))

            ban_count = 0
            skipped = 0
            skip_ids = [vip['user_id'] for vip in vips['data']] + [mod['user_id'] for mod in mods['data']]

            for message in messages:
                if int(message['tw_id']) in skip_ids:
                    skipped = skipped + 1
                    continue

                self.logger.info('Banning user {} {}'.format(message['name'], message['tw_id']))
                try:
                    await self.api.twitch.ban_user(broadcaster_id=self.context.channel.tw_id,
                                                   user_id=message['tw_id'],
                                                   duration=0,
                                                   reason='Mass ban requested by {}'.format(self.context.user.name))
                    ban_count = ban_count + 1
                except Exception as ex:
                    self.logger.error(ex)

                await asyncio.sleep(0.6)

            await self.context.reply('{} mass ban finished, banned {} users, skipped {} users. SirUwU'.format(self.context.user.name, ban_count, skipped))
            await self.db.saveTwitchMassBan(self.context.channel.channel_id, self.context.user.db_info['user_id'], search_text, 0, ban_count)
        except Exception as e:
            self.logger.info(self.context)
            self.logger.exception(e)

