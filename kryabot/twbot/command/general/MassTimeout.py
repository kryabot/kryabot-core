import asyncio

from twbot.command.AccessType import AccessType
from twbot.command.CommandBase import CommandBase


class MassBan(CommandBase):
    names = ['mtimeout']
    access = AccessType.mod_package()

    def __init__(self, context):
        super().__init__(context)

    async def process(self):
        try:
            search_text = self.get_word_list()
            if len(search_text) < 4:
                await self.context.reply('Search text is too short! Must be longer than 4')
                return

            viewers = await self.api.twitch.get_channel_chatters(self.context.channel.channel_name)
            viewers = viewers['chatters']
            ignore_users = viewers['moderators'] + viewers['staff'] + viewers['admins'] + viewers['global_mods'] + [self.context.channel.channel_name]

            ban_time = 600
            try:
                if search_text[0].isnumeric():
                    ban_time = int(search_text[0])
            except:
                ban_time = 600

            search_text = '%{}%'.format(search_text)
            self.logger.info('Searching messages to ban for {} like {}'.format(ban_time, search_text))
            messages = await self.db.searchTwitchMessages(self.context.channel.channel_id, search_text)
            self.logger.info('Received {} users to ban'.format(len(messages)))
            if messages is None or len(messages) == 0:
                await self.context.reply('{} no users found for mass ban!'.format(self.context.user.name))
                return
            else:
                await self.context.reply('{} starting to ban {} users ({})'.format(self.context.user.name, len(messages),
                                                                             'perm' if ban_time == 0 else (str(ban_time) + 's')))

            ban_count = 0
            skipped = 0

            def can_skip(name)->bool:
                for ignored in ignore_users:
                    if str(name).lower() == str(ignored).lower():
                        return True

                return False

            for message in messages:
                if can_skip(message['name']):
                    skipped = skipped + 1
                    continue

                self.logger.info('Banning user {}'.format(message['name']))
                try:
                    if ban_time > 0:
                        await self.context.channel.timeout(message['name'], ban_time, 'Mass ban required by {}'.format(self.context.user.name))
                    else:
                        await self.context.ban(message['name'], 'Mass ban required by {}'.format(self.context.user.name))

                    ban_count = ban_count + 1
                except Exception as ex:
                    self.logger.error(ex)

                await asyncio.sleep(0.3)

            await self.context.reply('{} mass ban finished, banned {} users, skipped {} users.'.format(self.context.user.name, ban_count, skipped))
            await self.db.saveTwitchMassBan(self.context.channel.channel_id, self.context.user.db_info['user_id'], search_text, ban_time, ban_count)
        except Exception as e:
            self.logger.info(self.context)
            self.logger.exception(e)

