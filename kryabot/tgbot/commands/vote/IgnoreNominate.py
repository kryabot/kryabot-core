from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand


class IgnoreNominate(BaseCommand):
    command_names = ['ignorenominate']
    access_level = UserAccess.CHAT_ADMIN

    def __init__(self, event, parsed):
        super().__init__(event, parsed, IgnoreNominate.access_level)
        self.must_be_reply = True

    async def process(self):
        await self.fetch_data()

        if not (await self.can_process()):
            return

        existing_votes = await self.db.getTgVoteActive(self.channel['channel_id'])
        if existing_votes is None or len(existing_votes) == 0:
            await self.reply_fail(self.get_translation('CMD_NOMINATE_VOTE_NOT_ACTIVE'))
            return

        existing_vote = existing_votes[0]

        target = await self.db.getUserByTgChatId(self.reply_message.from_id)
        if target is None or len(target) == 0:
            await self.reply_fail(self.get_translation("CMD_NOMINATE_NOT_VERIFIED"))
            return

        target = target[0]
        await self.db.addTgVoteIgnore(existing_vote['tg_vote_id'], target['user_id'], self.sender['user_id'])
        await self.reply_success(self.get_translation('CMD_NOMINATE_IGNORE_SUCCESS'))