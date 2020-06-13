from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand


class Award(BaseCommand):
    command_names = ['award']
    access_level = UserAccess.CHAT_ADMIN

    def __init__(self, event, parsed):
        super().__init__(event, parsed, Award.access_level)
        self.must_be_reply = True

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
            award_count = int(self.parsed.pop(2))
        except:
            award_count = 1

        existing_awards = await self.db.getChannelTgAwards(self.channel['channel_id'], self.channel['user_id'])

        for award in existing_awards:
            if keyword.lower() == award['award_key'].lower():
                await self.db.setTgAwardForUser(award['tg_award_id'], self.reply_message.from_id, award_count)
                await self.reply_success(self.get_translation('KB_AWARD_GIVEN').format(key=keyword, count=award_count))
                return

        await self.reply_fail(self.get_translation('CMD_AWARD_NOT_FOUND').format(oldkey=keyword))
