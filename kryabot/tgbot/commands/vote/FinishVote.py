from telethon.tl.types import PeerUser

from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand
from utils.formatting import format_user_label


class FinishVote(BaseCommand):
    command_names = ['finishvote']
    access_level = UserAccess.CHAT_ADMIN

    def __init__(self, event, parsed):
        super().__init__(event, parsed, FinishVote.access_level)

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return

        existing_votes = await self.db.getTgVoteActive(self.channel['channel_id'])
        if existing_votes is None or len(existing_votes) == 0:
            await self.reply_fail(self.get_translation('CMD_FINISH_VOTE_NOT_ACTIVE'))
            return

        existing_vote = existing_votes[0]

        await self.db.finishTgVote(existing_vote['tg_vote_id'])

        nominee_list = await self.db.getTgVoteNominees(existing_vote['tg_vote_id'])

        text = 'TOP 3'
        if nominee_list is not None:
            i = 0
            for nominee in nominee_list:
                if nominee['type'] == 'IGNORE':
                    continue

                i += 1
                if nominee['tg_id'] is not None:
                    user_entity = await self.client.get_entity(PeerUser(int(nominee['tg_id'])))
                    user_label = await format_user_label(user_entity)
                else:
                    user_label = nominee['dname'] if nominee['dname'] is not None else nominee['name']
                vote_count_label = self.get_translation('CMD_GET_VOTE_VOTE_LABEL').format(votes=nominee['votes'])
                text += '\n{}. {} {}'.format(i, user_label, vote_count_label)

                if i == 3:
                    break

        text = self.get_translation('CMD_FINISH_VOTE_SUCCESS') + '\n\n' + text
        await self.reply_success(text)
