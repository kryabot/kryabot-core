import asyncio

from telethon.errors import ChannelPrivateError

from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand
from tgbot.constants import TG_GROUP_CACHE_ID


class KbGetAll(BaseCommand):
    command_names = ['kbgetall']
    access_level = UserAccess.VERIFIED

    def __init__(self, event, parsed):
        super().__init__(event, parsed, KbGetAll.access_level)

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return

        records = await self.db.getAllTgGetters(self.channel['user_id'])

        answer = self.get_translation('KB_ALL_TITLE')
        answer += '\n\n'

        for record in records:
            if record['original_msg_id'] is not None and len(record['original_msg_id']) > 0 and record['original_msg_id'] != '0' \
            or record['cache_message_id'] is not None and len(record['cache_message_id']) > 0 and record['cache_message_id'] != '0':
                if record['broken'] == 1:
                    answer += "<s>{kw}</s>, ".format(kw=record['keyword'])
                else:
                    answer += "<b>{kw}</b>, ".format(kw=record['keyword'])
            else:
                answer += "{kw}, ".format(kw=record['keyword'])

        answer = answer.strip()
        if answer.endswith(','):
            answer = answer[:-1]

        await self.event.reply(answer)

        ## DATAPATCH

        # if self.sender['user_id'] != 4673:
        #     return
        #
        # groups = await self.client.get_all_auth_channels()
        #
        # for group in groups:
        #     rows = await self.db.getAllTgGetters(group['user_id'])
        #
        #     for row in rows:
        #         if row['cache_message_id'] is not None and len(row['cache_message_id']) > 0 and row['cache_message_id'] != '0':
        #             continue
        #
        #         if row['broken'] == 1:
        #             continue
        #
        #         if row['original_msg_id'] is not None and len(row['original_msg_id']) > 0 and row['original_msg_id'] != '0':
        #              try:
        #                 org_msg = await self.client.get_messages(group['tg_chat_id'], ids=int(row['original_msg_id']))
        #              except ChannelPrivateError:
        #                  org_msg = None
        #
        #              if org_msg is None:
        #                  await self.db.query('mark_getter_broken', [row['tg_get_id']])
        #                  self.logger.info('ERR In channel {} marking {} as broken, not found original message'.format(group['channel_name'], row['keyword']))
        #              else:
        #                  try:
        #                     cached_message = await self.client.send_message(TG_GROUP_CACHE_ID, org_msg)
        #                     await self.db.query('set_getter_cache_id', [str(cached_message.id), row['tg_get_id']])
        #                     self.logger.info('OK In channel {} updated {} cache successfully'.format(group['channel_name'], row['keyword']))
        #                  except TypeError:
        #                      self.logger.info('ERR In channel {} marking {} as broken due to type error'.format(group['channel_name'], row['keyword']))
        #                      await self.db.query('mark_getter_broken', [row['tg_get_id']])
        #                  except Exception as e:
        #                      self.logger.exception(e)
        #
        #              await asyncio.sleep(3)



