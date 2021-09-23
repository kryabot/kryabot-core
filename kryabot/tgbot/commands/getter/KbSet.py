from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand
from tgbot.constants import TG_GROUP_CACHE_ID


class KbSet(BaseCommand):
    command_names = ['kbset']
    access_level = UserAccess.VERIFIED

    def __init__(self, event, parsed):
        super().__init__(event, parsed, KbSet.access_level)
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

        if len(keyword.strip()) > 100:
            await self.reply_fail(self.get_translation('KB_KEYWORD_TOO_LONG').format(maxsym=100))
            return

        records = await self.db.getAllTgGetters(self.channel['user_id'])
        if len(records) >= 1000:
            await self.reply_fail(self.get_translation('KB_LIMIT').format(getlim=1000))
            return

        existing_records = await self.db.getTgGetter(self.channel['channel_id'], keyword)
        if len(existing_records) > 0:
            await self.reply_fail(self.get_translation('KB_DUPLICATE_KEYWORD'))
            return

        set_message = await self.event.message.get_reply_message()
        set_text = set_message.message

        cached_id = 0
        if set_message.media:
            try:
                cached_message = await self.client.send_message(TG_GROUP_CACHE_ID, set_message)
            except TypeError as wrongType:
                await self.reply_fail(self.get_translation('KB_UNSUPPORTED_MEDIA'))
                return
            cached_id = cached_message.id
            set_text = cached_message.message
        else:
            if set_text is None or set_text == '':
                await self.reply_fail(self.get_translation('KB_MISSING_TEXT'))
                return

        await self.db.setTgGetter(self.channel['channel_id'], keyword, set_text, cached_id, self.sender['user_id'], int(await self.is_chatadmin()))
        await self.reply_success(self.get_translation('KB_SET_SUCCESS').format(kw=keyword))
