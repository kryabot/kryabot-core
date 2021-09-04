from typing import Dict, List

from twbot.object.MessageContext import MessageContext
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

    async def process_bits(self, context: MessageContext):
        nt = Notice(None)
        nt.msg_param_months = context.get_bits()
        nt.display_name = context.user.display_name
        nt.login = context.user.name
        nt.msg_id = 'bits'

        await self.process(context, nt)

    async def process(self, context: MessageContext, notice: Notice):
        try:
            if notice.msg_id in ('sub', 'resub'):
                nt = notice.msg_param_sub_plan
            else:
                nt = notice.msg_id

            notice_type = self.get_notice_type(str(nt))
            resp = None
            if notice_type is not None:
                resp = await self.get_base_response(context.channel.channel_id, notice_type['notice_type_id'], await notice.get_notice_count_int())

            if resp is None or len(resp) == 0:
                resp = context.channel.default_notice_text

            if resp is None or len(resp) == 0:
                return

            resp = await self.replace_keywords(resp, notice)

            if len(resp) > 0:
                await context.reply(resp)
        except Exception as ex:
            self.logger.exception(ex)

    async def replace_keywords(self, answer, notice):
        answer = self.replace_keyword(answer, '#promo#', await avoid_none(notice.msg_param_promo_name))
        answer = self.replace_keyword(answer, '#user#', await notice.get_user_name())
        answer = self.replace_keyword(answer, '#giftreceiver#', await notice.get_gift_receiver())
        answer = self.replace_keyword(answer, '#count#', await notice.get_notice_count())
        answer = self.replace_keyword(answer, '#goal_current#', await notice.get_goal_current())
        answer = self.replace_keyword(answer, '#goal_target#', await notice.get_goal_target())
        answer = self.replace_keyword(answer, '#goal_remaining#', await notice.get_goal_remaining())
        answer = self.replace_keyword(answer, '#goal_added#', await notice.get_goal_added())

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

    def replace_keyword(self, answer, keyword, value):
        if keyword in answer:
            return answer.replace(keyword, str(value))
        return answer
