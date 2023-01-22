from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand
from utils.formatting import format_user_label


class AddVote(BaseCommand):
    command_names = ['addvote']
    access_level = UserAccess.VERIFIED

    def __init__(self, event, parsed):
        super().__init__(event, parsed, AddVote.access_level)

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return

        existing_votes = await self.db.getTgVoteActive(self.channel['channel_id'])
        if existing_votes is None or len(existing_votes) == 0:
            await self.reply_fail(self.get_translation('CMD_NOMINATE_VOTE_NOT_ACTIVE'))
            return

        existing_vote = existing_votes[0]

        if self.event.message.is_reply:
            message = await self.event.message.get_reply_message()
            target = await self.db.getUserByTgChatId(message.sender_id)
            if target is None or len(target) == 0:
                await self.reply_fail(self.get_translation('CMD_ADD_VOTE_NOT_VERIFIED'))
                return
            nominee = await self.db.getTgVoteNominee(existing_vote['tg_vote_id'], target[0]['user_id'])
            if nominee is None or len(nominee) == 0:
                await self.reply_fail(self.get_translation('CMD_ADD_VOTE_NOT_NOMINATED'))
                return

            nominee = nominee[0]
        else:
            try:
                num = int(self.parsed.pop(1))
            except Exception:
                num = 0

            if num <= 0:
                await self.reply_incorrect_input()
                return

            nominee_list = await self.db.getTgVoteNominees(existing_vote['tg_vote_id'])
            if nominee_list is None or len(nominee_list) < num:
                await self.reply_incorrect_input()
                return

            nominee = nominee_list[num - 1]

        if nominee is None:
            self.client.logger.error('Failed to find nominee')
            return

        await self.db.addTgVotePoint(existing_vote['tg_vote_id'], nominee['user_id'], self.sender['user_id'])

        nominee = await self.db.getTgVoteNominee(existing_vote['tg_vote_id'], nominee['user_id'])
        nominee = nominee[0]

        if nominee['tg_id'] is not None:
            user_entity = await self.client.get_entity(int(nominee['tg_id']))
            user_label = await format_user_label(user_entity)
        else:
            user_label = nominee['dname'] if nominee['dname'] is not None else nominee['name']

        await self.reply_success(self.get_translation('CMD_ADD_VOTE_SUCCESS').format(user=user_label, votes=nominee['votes']))
