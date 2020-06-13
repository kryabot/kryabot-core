from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand


class KbDel(BaseCommand):
    command_names = ['kbdel']
    access_level = UserAccess.VERIFIED

    def __init__(self, event, parsed):
        super().__init__(event, parsed, KbDel.access_level)

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return

        try:
            keyword = self.parsed.pop(1)
        except:
            await self.reply_fail(self.get_translation('KB_NO_KEYWORD'))
            return

        if keyword is None or len(keyword) == 0:
            await self.reply_fail(self.get_translation('KB_NO_KEYWORD'))
            return

        # Get record from DB
        record = await self.get_first(await self.db.getTgGetter(self.channel['channel_id'], keyword))
        if record is None:
            await self.reply_fail(self.get_translation('KB_KEYWORD_NOT_FOUND'))
            return

        await self.db.deleteTgGetter(self.channel['user_id'], record['tg_get_id'], self.sender['user_id'])
        await self.reply_success(self.get_translation('KB_DELETE_SUCCESS'))
