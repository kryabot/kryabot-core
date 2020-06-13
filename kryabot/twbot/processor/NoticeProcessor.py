from typing import Dict, List

from twbot.object.Channel import Channel
from twbot.object.Notice import Notice
from twbot.processor.Processor import Processor
from utils.value_check import avoid_none


class NoticeProcessor(Processor):
    def __init__(self):
        super().__init__()
        self.notices: Dict[int, List[Dict]] = {}
        self.notice_types: List[Dict] = []

    async def update(self, channel_id: int = None) -> None:
        self.logger.info('Updating data for channel {}'.format(channel_id))

        notice_rows = await self.db.getChannelNotices()

        self.notices = self.init_struct(self.notices, channel_id)
        self.notices = self.add_data(self.notices, notice_rows)

        self.notice_types = await self.db.getNoticeTypes()

        self.logger.debug('Notice data: {}'.format(self.notices))
        self.ready = True

    async def process_bits(self, irc_data, db_channel, db_user, count):
        nt = Notice(None)
        nt.msg_param_months = count
        nt.display_name = irc_data.author.display_name
        nt.login = irc_data.author.name
        nt.msg_id = 'bits'

        await self.process(irc_data, db_channel, db_user, nt)

    async def process(self, irc_data, channel: Channel, db_user, notice: Notice):
        try:
            if notice.msg_id in ('sub', 'resub'):
                nt = notice.msg_param_sub_plan
            else:
                nt = notice.msg_id

            notice_type = self.get_notice_type(str(nt))
            resp = None
            if notice_type is not None:
                resp = await self.get_base_response(channel.channel_id, notice_type['notice_type_id'], await notice.get_notice_count_int())

            if resp is None or len(resp) == 0:
                resp = channel.default_notice_text

            if resp is None or len(resp) == 0:
                return

            resp = await self.replace_keywords(resp, notice)

            if len(resp) > 0:
                await irc_data.send(resp)
        except Exception as ex:
            self.logger.exception(ex)

    async def replace_keywords(self, answer, notice):
        answer = answer.replace('#promo#', await avoid_none(notice.msg_param_promo_name))
        answer = answer.replace('#user#', await notice.get_user_name())
        answer = answer.replace('#giftreceiver#', await notice.get_gift_receiver())
        answer = answer.replace('#count#', await notice.get_notice_count())
        return answer

    async def get_base_response(self, channel_id: int, notice_type_id: int, count: int)->str:
        if channel_id not in self.notices:
            return ''

        for note in self.notices[channel_id]:
            if note['notice_type_id'] != notice_type_id:
                continue
            if note['count_from'] > count:
                continue
            if note['count_to'] < count:
                continue
            return note['reply']

        return ''

    def get_notice_type(self, notice_name):
        for notice_type in self.notice_types:
            if notice_type['notice_name'].lower() == notice_name.lower():
                return notice_type

        self.logger.error('Received unknown notice type: {}'.format(notice_name))
        return None