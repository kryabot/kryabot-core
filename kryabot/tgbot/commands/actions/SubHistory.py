from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand


class SubHistory(BaseCommand):
    command_names = ['subhistory']
    access_level = UserAccess.CHAT_ADMIN

    def __init__(self, event, parsed):
        super().__init__(event, parsed, SubHistory.access_level)
        self.must_be_reply = True

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return

        target = await self.db.getUserByTgChatId(self.reply_message.sender_id)
        if target is None or len(target) == 0:
            await self.reply_fail(self.get_translation("CMD_SUB_HISTORY_NOT_VERIFIED"))
            return

        # Join two list results and order by timestamp

        datetime_string_format = '%Y-%m-%d %H:%M:%S'

        data_rows = await self.db.getTwitchSubHistoryRecords(self.channel['channel_id'], target[0]['user_id'])
        notification_rows = await self.db.getTwitchSubNotificationHistory(self.channel['channel_id'], target[0]['user_id'])

        result_rows = []
        if data_rows is not None:
            for data in data_rows:
                obj = {}
                obj['type'] = self.parse_event_type(data['event_type'])
                obj['is_gift'] = data['is_gift']
                obj['ts'] = data['event_ts'].strftime(datetime_string_format)

                result_rows.append(obj)

        if notification_rows is not None:
            for notification in notification_rows:
                obj = {}
                obj['type'] = 'NOTIFICATION' if notification['notice_type'] != 'subgift' else 'SUBSCRIBE'
                obj['is_gift'] = 1 if notification['notice_type'] == 'subgift' else 0
                obj['ts'] = notification['ts'].strftime(datetime_string_format)

                result_rows.append(obj)

        if result_rows is None or len(result_rows) == 0:
            await self.event.reply(self.get_translation('CMD_SUB_HISTORY_EMPTY'))
            return

        text = "{} {}\n\n".format(self.get_translation('CMD_SUB_HISTORY_TITLE'), target[0]['dname'] if target[0]['dname'] is not None else target[0]['name'])
        result_rows = sorted(result_rows, key=lambda row: row['ts'], reverse=True)
        for data in result_rows:
            text += "{} {}".format(data['ts'], self.get_translation('CMD_SUB_HISTORY_TYPE_{}'.format(data['type'])))
            if data['is_gift']:
                text += ' (gift)'
            text += '\n'

        await self.event.reply(text, link_preview=False)

    def parse_event_type(self, event_type):
        try:
            return event_type.split('.')[-1].upper()
        except Exception as ex:
            return 'unknown'

