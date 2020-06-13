from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand


class CreateVote(BaseCommand):
    command_names = ['createvote']
    access_level = UserAccess.CHAT_ADMIN

    def __init__(self, event, parsed):
        super().__init__(event, parsed, CreateVote.access_level)

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return

        try:
            description = await self.get_text_after_command()
        except:
            description = ''

        if description is None or description == '':
            await self.reply_fail(self.get_translation('CMD_CREATE_VOTE_NO_DESCRIPTION'))
            return

        existing_votes = await self.db.getTgVoteActive(self.channel['channel_id'])
        if len(existing_votes) > 0:
            await self.reply_fail(self.get_translation('CMD_CREATE_VOTE_HAS_ACTIVE'))
            return

        await self.db.createTgVote(self.channel['channel_id'], description, self.sender['user_id'])
        await self.reply_success(self.get_translation('CMD_CREATE_VOTE_SUCCESS'))