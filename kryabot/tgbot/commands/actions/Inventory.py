import asyncio

from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand


class Inventory(BaseCommand):
    command_names = ['inventory']
    access_level = UserAccess.VERIFIED

    def __init__(self, event, parsed):
        super().__init__(event, parsed, Inventory.access_level)

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return

        if await self.db.is_cooldown_inventory(self.channel['tg_chat_id'], self.event.from_id):
            return

        await self.db.set_inventory_cooldown(self.channel['tg_chat_id'], self.event.from_id)

        datas = await self.db.getUserAllCurrency(self.sender['user_id'])
        if datas is None or not datas:
            message = await self.event.reply(self.get_translation("CMD_INVENTORY_EMPTY"))
            try:
                await asyncio.sleep(120)
                await message.delete()
                await self.event.delete()
            except:
                pass
            return

        text = self.get_translation("CMD_INVENTORY_CONTAINS") + "\n"
        for data in datas:
            text += "{} {}: {}\n".format(self.get_currency_emote(data['currency_key']), self.get_translation("INVENTORY_ITEM_" + str(data['currency_key']).capitalize()), int(data['currency']))

        message = await self.event.reply(text, link_preview=False)

        try:
            await asyncio.sleep(120)
            await message.delete()
            await self.event.delete()
        except:
            pass

    def get_currency_emote(self, currency_name: str):
        return {"egg": "🥚",
                "pumpkin": "🎃"}.get(currency_name, "📦")
