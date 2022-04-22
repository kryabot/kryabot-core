import asyncio

from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand
from tgbot.commands.items.ItemMap import get_item_emote


class TopEggs(BaseCommand):
    command_names = ['topeggs']
    access_level = UserAccess.VERIFIED

    def __init__(self, event, parsed):
        super().__init__(event, parsed, TopEggs.access_level)

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return
        count = 20
        datas = await self.db.get_top_currency_owners('egg_2021', count)
        if datas:
            text = "Top{} collected eggs during 2022 Easter event:\n".format(count)
            i = 1
            for data in datas:
                text += "{}. {} ({})\n".format(i, data['dname'] if data['dname'] else data['name'], int(data['amount']))
                i += 1

            message = await self.event.reply(text, link_preview=False)

            try:
                await asyncio.sleep(120)
                await message.delete()
                await self.event.delete()
            except:
                pass
