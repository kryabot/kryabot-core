from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand


class OpenNominations(BaseCommand):
    command_names = ['opennominations']
    access_level = UserAccess.CHAT_ADMIN

    def __init__(self, event, parsed):
        super().__init__(event, parsed, OpenNominations.access_level)

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return

        existing_votes = await self.db.getTgVoteActive(self.channel['channel_id'])
        if existing_votes is None or len(existing_votes) == 0:
            await self.reply_fail(self.get_translation('CMD_OPEN_NOMINATIONS_NOT_ACTIVE'))
            return

        existing_vote = existing_votes[0]

        await self.db.tgVoteOpenNominations(existing_vote['tg_vote_id'])
        await self.reply_success(self.get_translation('CMD_OPEN_NOMINATIONS_SUCCESS'))