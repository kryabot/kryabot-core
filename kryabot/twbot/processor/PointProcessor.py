from typing import List, Dict

from twbot.processor.Processor import Processor


class PointProcessor(Processor):
    def __init__(self):
        super().__init__()

        self.actions: Dict[int, List[Dict]] = {}
        self.user_input_key = 'user_input'

    async def process(self, db_channel, db_user, redeption_data)->None:
        self.logger.debug('Received new channel point redemption: {}'.format(redeption_data))

        action_list = await self.get_action_list(db_channel.channel_id, redeption_data['reward']['title'])

        self.logger.debug('Filtered actions list: {}'.format(action_list))

        for action in action_list:
            action_func = await self.get_action(action['action'])
            if action_func is None:
                self.logger.error('Failed to find action function by keyword {}'.format(action['action']))
                return

            await action_func(db_channel, db_user, redeption_data, action)

    async def get_action(self, action_type):
        self.logger.debug('Searching action for key {}'.format(action_type))

        return {'TWITCH_MUTE_SELF': self.action_twitch_mute_self,
                'TWITCH_MUTE_OTHER': self.action_twitch_mute_other,
                'TWITCH_SUBMOD_ON': None,
                'TWITCH_SUBMOD_OFF': None,
                'TWITCH_RAID': None,
                'TWITCH_MESSAGE': self.action_twitch_message,
                'TG_MUTE_SELF': self.action_tg_mute_self,
                'TG_MUTE_OTHER': self.action_tg_mute_other,
                'TG_MESSAGE': self.action_tg_message,
                'TG_AWARD': self.action_tg_award
                }.get(action_type, None)

    async def update(self, channel_id: int = None):
        self.logger.info('Updating data for channel {}'.format(channel_id))
        new_rows = await self.db.getChannelPointActions(channel_id)

        self.actions = self.init_struct(self.actions, channel_id)
        self.actions = self.add_data(self.actions, new_rows)

        self.logger.debug('Point action data: {}'.format(self.actions))
        self.ready = True

    async def get_action_list(self, channel_id: int, title: str)->List:
        if channel_id not in self.actions:
            return []

        main_action = await self.find_action_by_title(channel_id, title)

        if main_action is None or main_action == {}:
            return []

        list = [main_action]

        # child_actions = await self.get_child_actions(channel_id, main_action['channel_point_action_id'])
        #
        # if child_actions is None:
        #     return list
        #
        # for child in child_actions:
        #     list.append(child)

        return list

    async def find_action_by_title(self, channel_id: int, title: str)->Dict:
        # Invalid input
        if channel_id is None:
            return {}

        # Search by title
        for action in self.actions[channel_id]:
            if action['title'] == title and action['parent_id'] == 0 and action['enabled'] == 1:
                return action

        return {}

    async def get_child_actions(self, channel_id: int, parent_id: int)->List:
        child_list = []

        # Invalid input
        if channel_id is None:
            return child_list

        # Get childs of main parent
        for action in self.actions[channel_id]:
            if action['channel_point_action_id'] == parent_id and action['enabled'] == 1:
                child_list.append(action)

        return child_list

    def replace_message_tags(self, message, username, amount, user_input):
        message = message.replace('#username#', str(username))
        message = message.replace('#amount#', str(amount))
        message = message.replace('#input#', str(user_input))

        return message

    async def valid_input(self, db_channel, redemption_data):
        if self.user_input_key not in redemption_data:
            await self.irc.send_privmsg(db_channel.channel_name, content='Reward cannot be completed! {} reward must have user input where redeemer could enter username.'.format(db_channel.channel_name))
            return False

        if redemption_data[self.user_input_key] is None or redemption_data[self.user_input_key] == '':
            await self.irc.send_privmsg(db_channel.channel_name, content='Reward cannot be completed! Mandatory input from {} was not entered.'.format(redemption_data['user']['login']))
            return False

        return True

    async def tg_group_exists(self, db_channel):
        group = await self.db.getTgChatIdByChannelId(db_channel.channel_id)
        if group is None or len(group) == 0:
            self.irc.send_privmsg(db_channel.channel_name, content='Reward cannot be completed! This channel has no linked Telegram group.')
            return False

        return True

    #
    # Actions
    #

    async def action_twitch_message(self, db_channel, db_user, redemption_data, action):
        user_input = ''
        if self.user_input_key in redemption_data:
            user_input = redemption_data[self.user_input_key]

        if action['data'] is not None and len(action['data']) > 0:
            await self.irc.send_privmsg(db_channel.channel_name, content=self.replace_message_tags(action['data'], redemption_data['user']['login'], action['amount'], user_input))

    async def action_twitch_mute_self(self, db_channel, db_user, redemption_data, action):
        await self.irc.send_privmsg(db_channel.channel_name, content='.timeout {} {} {}'.format(redemption_data['user']['login'], int(action['amount']), redemption_data['reward']['title']))
        await self.action_twitch_message(db_channel, db_user, redemption_data, action)

    async def action_twitch_mute_other(self, db_channel, db_user, redemption_data, action):
        if not self.valid_input(db_channel, redemption_data):
            return

        try:
            nickname = redemption_data['user_input'].split(' ')[0]
        except Exception as ex:
            nickname = redemption_data['user_input']

        if nickname.startswith('@'):
            nickname = nickname[1:]

        await self.irc.send_privmsg(db_channel.channel_name, content='.timeout {} {} {}'.format(nickname, int(action['amount']), redemption_data['reward']['title']))
        await self.action_twitch_message(db_channel, db_user, redemption_data, action)

    async def action_tg_mute_self(self, db_channel, db_user, redemption_data, action):
        if not await self.tg_group_exists(db_channel):
            return

        pass

    async def action_tg_mute_other(self, db_channel, db_user, redemption_data, action):
        if not await self.tg_group_exists(db_channel):
            return

        if not await self.valid_input(db_channel, redemption_data):
            return

        pass

    async def action_tg_message(self, db_channel, db_user, redemption_data, action):
        if not await self.tg_group_exists(db_channel):
            return

        if not await self.valid_input(db_channel, redemption_data):
            return


    async def action_tg_award(self, db_channel, db_user, redemption_data, action):
        if not await self.tg_group_exists(db_channel):
            return

        if not self.valid_input(db_channel, redemption_data):
            return

        pass