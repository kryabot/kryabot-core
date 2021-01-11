import asyncio

from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand
from tgbot.commands.items.ItemMap import get_item_emote


class ChatInventory(BaseCommand):
    command_names = ['chatinventory']
    access_level = UserAccess.CHAT_ADMIN

    def __init__(self, event, parsed):
        super().__init__(event, parsed, ChatInventory.access_level)

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return

        datas = await self.db.getTgChatCurrency(self.channel['channel_id'])
        if datas is None:
            message = await self.event.reply(self.get_translation("CMD_CHAT_INVENTORY_EMPTY"))
        else:
            text = self.get_translation("CMD_CHAT_INVENTORY_CONTAINS") + "\n"
            for data in datas:
                text += "{} {}: {}\n".format(get_item_emote(data['currency_key']), self.get_translation("INVENTORY_ITEM_" + str(data['currency_key']).upper()), int(data['amt']))

            message = await self.event.reply(text, link_preview=False)

        sticker_set = await self.client.get_sticker_set('GiveMeTheBins')
        for sticker in sticker_set.documents:
            if sticker.id == 1299861509853151283:
                await self.client.send_message(self.channel['tg_chat_id'], file=sticker, reply_to=message.id)
                break

        try:
            await asyncio.sleep(300)
            await message.delete()
            await self.event.delete()
        except:
            pass

