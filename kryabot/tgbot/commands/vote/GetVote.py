from telethon.tl.types import PeerUser

from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand
from utils.formatting import format_user_label


class GetVote(BaseCommand):
    command_names = ['getvote']
    access_level = UserAccess.VERIFIED

    def __init__(self, event, parsed):
        super().__init__(event, parsed, GetVote.access_level)

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return

        existing_votes = await self.db.getTgVoteActive(self.channel['channel_id'])
        if existing_votes is None or len(existing_votes) == 0:
            await self.reply_fail(self.get_translation('CMD_GET_VOTE_NOT_ACTIVE'))
            return

        existing_vote = existing_votes[0]

        text = existing_vote['description']

        if existing_vote['open_nominations'] == 1:
            text += '\n\n{}: {}'.format(self.get_translation('CMD_GET_VOTE_NOMINATION_TITLE'),
                                        self.get_translation('GENERAL_YES'))
        else:
            text += '\n\n{}: {}'.format(self.get_translation('CMD_GET_VOTE_NOMINATION_TITLE'),
                                        self.get_translation('GENERAL_NO'))

        nominee_list = await self.db.getTgVoteNominees(existing_vote['tg_vote_id'])

        total_nominees = 0
        total_votes = 0
        list_text = "\n\n{}".format(self.get_translation('CMD_GET_VOTE_NOMINATION_LIST_TITLE'))
        if nominee_list is not None:
            for nominee in nominee_list:
                if nominee['type'] == 'IGNORE':
                    continue

                total_nominees += 1
                total_votes += nominee['votes']

                if nominee['tg_id'] is not None:
                    user_entity = await self.client.get_entity(PeerUser(int(nominee['tg_id'])))
                    user_label = await format_user_label(user_entity)
                else:
                    user_label = nominee['dname'] if nominee['dname'] is not None else nominee['name']
                vote_count_label = self.get_translation('CMD_GET_VOTE_VOTE_LABEL').format(votes=nominee['votes'])
                list_text += '\n{}. {} {}'.format(total_nominees, user_label, vote_count_label)

        text += '\n{}: {}'.format(self.get_translation('CMD_GET_VOTE_TOTAL_NOMINEES'), total_nominees)
        text += '\n{}: {}'.format(self.get_translation('CMD_GET_VOTE_TOTAL_VOTES'), total_votes)

        if total_nominees > 0:
            text += list_text

        await self.event.reply(text, link_preview=False)
