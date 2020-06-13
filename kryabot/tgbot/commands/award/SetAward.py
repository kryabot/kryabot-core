from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand


class SetAward(BaseCommand):
    command_names = ['setaward']
    access_level = UserAccess.CHAT_ADMIN

    def __init__(self, event, parsed):
        super().__init__(event, parsed, SetAward.access_level)

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return

        try:
            keyword = self.parsed.pop(1)
        except:
            await self.reply_fail(self.get_translation('KB_NO_KEYWORD'))
            return

        try:
            text = await self.get_text_after_command()
        except:
            text = ''

        if text is None or text == '':
            await self.reply_fail(self.get_translation('CMD_INCORRECT_INPUT'))
            return

        existing_awards = await self.db.getChannelTgAwards(self.channel['channel_id'], self.channel['user_id'])
        award = [awd for awd in existing_awards if awd['award_key'].lower() == keyword.lower()]

        if existing_awards is None or len(award) == 0:
            await self.db.updateAward(self.channel['user_id'], None, keyword, text, self.sender['user_id'])
        else:
            await self.db.updateAward(self.channel['user_id'], award[0]['tg_award_id'], keyword, text, self.sender['user_id'])

        await self.db.getChannelTgAwards(channel_id=self.channel['channel_id'], user_id=self.channel['user_id'], skip_cache=True)
        await self.reply_success(self.get_translation('CMD_ADD_AWARD_SUCCESS').format(award_keyword=keyword, award_template=text))

