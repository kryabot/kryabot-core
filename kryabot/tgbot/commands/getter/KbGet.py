from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand
from tgbot.constants import TG_GROUP_CACHE_ID


class KbGet(BaseCommand):
    command_names = ['kbget']
    access_level = UserAccess.VERIFIED

    def __init__(self, event, parsed):
        super().__init__(event, parsed, KbGet.access_level)

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return

        if await self.db.is_cooldown_getter(self.channel['tg_chat_id']):
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

        if self.event.message.is_reply:
            answer_to = await self.event.message.get_reply_message()
            if answer_to is None:
                answer_to = self.event.message
            else:
                try:
                    await self.client.delete_messages(self.event.message.to_id.channel_id, self.event.message.id)
                except:
                    pass
        else:
            answer_to = self.event.message

        await self.db.set_getter_cooldown(self.channel['tg_chat_id'], seconds=self.channel['getter_cooldown'])

        cached_message = None
        if record['cache_message_id'] is not None and len(record['cache_message_id']) > 0 and record['cache_message_id'] != '0':
            cached_message = await self.client.get_messages(TG_GROUP_CACHE_ID, ids=int(record['cache_message_id']))
        elif record['original_msg_id'] is not None and len(record['original_msg_id']) > 0 and record['original_msg_id'] != '0':
            cached_message = await self.client.get_messages(self.channel['tg_chat_id'], ids=int(record['original_msg_id']))

        get_message_text = '<b>{kw}</b>'.format(kw=keyword)
        if record['text'] is not None and len(record['text']) > 0:
            get_message_text += '\n\n{data}'.format(data=record['text'])

        if cached_message is not None:
            if cached_message.text:
                cached_message.text = get_message_text

            await self.client.send_message(self.channel['tg_chat_id'], reply_to=answer_to, message=cached_message)
            return

        await self.client.send_message(self.channel['tg_chat_id'], reply_to=answer_to, message=get_message_text)