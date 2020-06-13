from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand


class Banmedia(BaseCommand):
    command_names = ['banmedia']
    access_level = UserAccess.CHAT_ADMIN

    def __init__(self, event, parsed):
        super().__init__(event, parsed, Banmedia.access_level)
        self.must_be_reply = True

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return

        if self.reply_message.media is None:
            return

        try:
            text = await self.get_text_after_command()
        except:
            text = ''

        if text is None or text == '':
            await self.reply_fail(self.get_translation('CMD_BANMEDIA_NO_REASON'))
            return
        
        media_id, media_type, access_hash, file_ref, file_mime, file_size = await self.get_media_info(self.reply_message.media)

        await self.db.banTgMedia(self.channel['channel_id'], media_type, media_id, self.sender['user_id'], text)
        await self.client.init_banned_media(self.channel['channel_id'])
        await self.reply_success('{text}\nID: {id}'.format(type=media_type, text=self.get_translation('CMD_BANMEDIA_SUCCESS'), id=media_id))

        messages = await self.client.get_messages(self.event.message.to_id.channel_id, 1000)
        del_list = []
        for msg in messages:
            if msg.media is not None:
                id2, type2, access_hash, file_ref, file_mime, file_size = await self.get_media_info(msg.media)
                if await self.client.is_media_banned(self.channel['channel_id'], id2, type2):
                    del_list.append(msg.id)

        if len(del_list) > 0:
            await self.client.delete_messages(self.event.message.to_id.channel_id, del_list)