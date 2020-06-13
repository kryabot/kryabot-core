from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand


class GetAwards(BaseCommand):
    command_names = ['getawards']
    access_level = UserAccess.CHAT_ADMIN

    def __init__(self, event, parsed):
        super().__init__(event, parsed, GetAwards.access_level)

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return

        existing_awards = await self.db.getChannelTgAwards(self.channel['channel_id'], self.channel['user_id'])

        reply_message = ''
        for award in existing_awards:
            reply_message += '\n' + '[{award_keyword}] {award_template}'.format(award_keyword=award['award_key'],
                                                                                award_template=award['award_template'])

        if reply_message == '':
            await self.reply_fail(self.get_translation('CMD_AWARD_LIST_EMPTY'))
            return

        reply_message = '{text}: {reply_msg}'.format(reply_msg=reply_message, text=self.get_translation('CMD_AWARD_AVAIL'))
        await self.event.reply(reply_message)