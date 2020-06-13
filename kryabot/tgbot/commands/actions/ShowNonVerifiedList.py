from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand
from telethon.tl.types import PeerChannel
from utils.mappings import status_to_text
from utils.date_diff import get_datetime_diff_text
from datetime import datetime
from telethon.helpers import TotalList
import asyncio


class ShowNonVerifiedList(BaseCommand):
    command_names = ['shownonverifiedlist']
    access_level = UserAccess.CHAT_ADMIN

    def __init__(self, event, parsed):
        super().__init__(event, parsed, ShowNonVerifiedList.access_level)

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return

        if not await self.is_superadmin() and await self.db.is_cooldown_non_verified_list(self.channel['tg_chat_id']):
            await self.reply_fail(self.get_translation('CMD_COOLDOWN'))
            return

        counter = 0
        total_counter = 0
        reply_text = '<b>{text}:</b>'.format(text=self.get_translation('NOT_VERIFIED_USERS'))
        channel_entity = await self.client.get_entity(PeerChannel(self.channel['tg_chat_id']))
        participants = await self.client.get_participants(channel_entity)

        last_msg_label = self.get_translation('CMD_LAST_MESSAGE')
        suffix = self.get_translation('GENERAL_AGO')
        total_label = self.get_translation('UR_TOTAL')

        await self.db.set_non_verified_list_cooldown(self.channel['tg_chat_id'], seconds=600)

        for participant in participants:
            if participant.bot:
                continue

            if counter >= 100:
                await self.event.reply(reply_text, parse_mode='html')
                counter = 0
                reply_text = ''

            requestor = await self.db.getUserByTgChatId(participant.id)
            if len(requestor) == 0:
                total_counter += 1
                counter += 1
                reply_text += '\n' + '▪️{} ({})'.format(await self.format_html_user_mention(participant), self.get_translation(status_to_text(participant.status)))

                if participant.deleted is True:
                    reply_text += ' DELETED'
                else:
                    reply_text += ' {}: {}'.format(last_msg_label,await self.get_last_message_text(channel_entity, participant, ' ' + suffix, 'хз'))
                if total_counter % 10 == 0:
                    await asyncio.sleep(1)

        if counter > 0:
            await self.event.reply('{}\n\n{}: {}'.format(reply_text, total_label, total_counter))

        if total_counter == 0:
            await self.reply_success(self.get_translation('ALL_VERIFIED_USERS'))

    async def get_last_message_text(self, channel, user, text_after, text_not_found):
        last_message = await self.get_first(await self.client.get_messages(entity=channel, from_user=user, limit=1))
        if last_message is None or isinstance(last_message, TotalList):
            return text_not_found

        return (await get_datetime_diff_text(datetime1=datetime.now(tz=last_message.date.tzinfo), datetime2=last_message.date, max_size=1)) + text_after


