from telethon.tl.types import PeerChannel

from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand
import asyncio


class StartMasskick(BaseCommand):
    command_names = ['startmasskick']
    access_level = UserAccess.CHAT_SUDO

    def __init__(self, event, parsed):
        super().__init__(event, parsed, StartMasskick.access_level)

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return

        settings = 'Kick deleted accounts: yes'
        settings += '\nKick non-verified accounts: yes'
        settings += '\nKick non-follower users: {}'.format('yes' if self.channel['join_follower_only'] else 'no')
        settings += '\nKick non-subcribers: {}'.format('yes' if self.channel['join_sub_only'] else 'no')
        settings += '\n\n<b>Should i continue?</b> Reply me with yes/no'

        channel_entity = await self.client.get_entity(PeerChannel(int(self.channel['tg_chat_id'])))
        sender_id = self.event.message.sender_id

        try:
            async with self.client.conversation(channel_entity) as conv:
                question = await conv.send_message('Do you really want to start mass kick? Reply with Yes or No to this message!')

                answer = ''
                resp = None
                while answer not in ['yes', 'no']:
                    resp = await conv.get_reply(message=question)
                    if resp.sender_id != sender_id:
                        continue
                    answer = resp.raw_text.lower()
                if answer == 'yes':
                    setting_question = await conv.send_message(settings, reply_to=resp.id)
                    continue_answer = ''
                    while continue_answer not in ['yes', 'no']:
                        resp2 = await conv.get_reply(message=setting_question)
                        if resp2.sender_id != sender_id:
                            continue
                        continue_answer = resp2.raw_text.lower()
                    if continue_answer == 'yes':
                        params = []
                        params.append({'key': 'not_verified', 'enabled': 1})
                        params.append({'key': 'not_sub', 'enabled': self.channel['join_sub_only']})
                        params.append({'key': 'not_follower', 'enabled': self.channel['join_follower_only']})
                        params.append({'key': 'not_active', 'enabled': 1})
                        self.client.loop.create_task(self.client.run_channel_refresh(self.channel, True, params))
                        await self.reply_success('OK')
                    else:
                        await conv.send_message('you disappointed me...', reply_to=resp2.id)
                else:
                    await conv.send_message('you disappointed me...', reply_to=resp.id)
        except asyncio.TimeoutError as timeout:
            await self.reply_fail('You are too slow... try again.')


