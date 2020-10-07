from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand


class GetWarns(BaseCommand):
    command_names = ['getwarns']
    access_level = UserAccess.CHAT_ADMIN

    def __init__(self, event, parsed):
        super().__init__(event, parsed, GetWarns.access_level)
        self.must_be_reply = True

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return

        warns = await self.client.moderation.get_user_existing_warns(self.channel, self.reply_message.sender_id)
        if warns is None or len(warns) == 0:
            await self.event.reply(self.get_translation('CMD_USER_WARNS_EMPTY'))
            return

        answer = ''

        warn_auto = self.get_translation('CMD_USER_WARNS_AUTO')
        warn_manual = self.get_translation('CMD_USER_WARNS_MANUAL')

        total = 0
        for warn in warns:
            if warn['auto']:
                answer += warn_auto.format(warn['ts'])
            else:
                answer += warn_manual.format(warn['ts'])

            answer += '\n'
            total += 1

        await self.event.reply('{}\n{}: {}'.format(answer, self.get_translation('UR_TOTAL'), total))
