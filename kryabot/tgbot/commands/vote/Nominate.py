from telethon.tl.functions.channels import GetParticipantRequest
from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.base import BaseCommand


class Nominate(BaseCommand):
    command_names = ['nominate']
    access_level = UserAccess.VERIFIED

    def __init__(self, event, parsed):
        super().__init__(event, parsed, Nominate.access_level)
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
        if existing_vote['open_nominations'] == 0 and not await self.is_chatadmin() and not await self.is_superadmin():
            await self.reply_fail(self.get_translation('CMD_NOMINATE_NOT_ALLOWED'))
            return

        target = await self.db.getUserByTgChatId(self.reply_message.sender_id)
        if target is None or len(target) == 0:
            await self.reply_fail(self.get_translation("CMD_NOMINATE_NOT_VERIFIED"))
            return

        target = target[0]
        nominee = await self.db.getTgVoteNominee(existing_vote['tg_vote_id'], target['user_id'])

        try:
            tg_participant = await self.client(GetParticipantRequest(self.channel['tg_chat_id'], self.reply_message.sender_id))
        except Exception as ex:
            self.client.logger.error(str(ex))
            tg_participant = None

        if tg_participant is None:
            await self.reply_fail(self.get_translation('CMD_NOMINATE_NOT_PARTICIPANT'))
            return

        if nominee is None or len(nominee) == 0:
            await self.db.addTgVoteNominee(existing_vote['tg_vote_id'], target['user_id'], self.sender['user_id'])
            await self.reply_success(self.get_translation('CMD_NOMINATE_SUCCESS'))
            return

        nominee = nominee[0]
        if nominee['type'] == 'NOMINATE':
            await self.reply_fail(self.get_translation('CMD_NOMINATE_EXISTS'))
            return

        if nominee['type'] == 'IGNORE':
            if await self.is_chatadmin() or await self.is_superadmin():
                await self.db.addTgVoteNominee(existing_vote['tg_vote_id'], target['user_id'], self.sender['user_id'])
                await self.reply_success(self.get_translation('CMD_NOMINATE_SUCCESS'))
                return
            else:
                await self.reply_fail(self.get_translation('CMD_NOMINATE_IGNORED'))
                return

        # Unexpected path (most likely type)
        self.client.logger.info(str(nominee))
        self.client.logger.info(str(target))
        self.client.logger.error('Failed to nominate user, end of path.')