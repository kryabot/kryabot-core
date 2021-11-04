import enum

from telethon import events, Button
from urllib.parse import urlparse
from itertools import groupby

from infobot.tg_event_helpers import required_admin, required_infobot
from utils.array import get_first
from infobot.LinkTable import LinkTable


class FollowConfig:
    twitch_hostname = 'twitch.tv'
    boosty_hostname = 'boosty.to'
    allowed_hostnames = [twitch_hostname]


class MenuButton(enum.Enum):
    BUTTON_SHOW_FOLLOWING_TWITCH = Button.inline(text='Show Twitch.tv follows', data='menushowfollowstwitch')
    BUTTON_SHOW_FOLLOWING_BOOSTY = Button.inline(text='Show Boosty.to follows', data='menushowfollowsboosty')
    BUTTON_SHOW_FOLLOWING = Button.inline(text='Back', data='menushowfollowsoptions')

    @staticmethod
    def get_following_option_list():
        return [MenuButton.BUTTON_SHOW_FOLLOWING_TWITCH, MenuButton.BUTTON_SHOW_FOLLOWING_BOOSTY]


def register_events(client):
    client.add_event_handler(command_follow)
    client.add_event_handler(command_show_following)
    client.add_event_handler(query_show_following_boosty)
    client.add_event_handler(query_show_following_twitch)
    client.add_event_handler(query_show_following)
    client.add_event_handler(pong)


@events.register(events.NewMessage(pattern='/ping'))
async def pong(event):
    await event.answer('pong')


@events.register(events.NewMessage(pattern='/follow', func=lambda e: not e.is_private))
@required_admin()
@required_infobot()
async def command_follow(event: events.NewMessage.Event, infobot):

    words = event.raw_text.split(' ')
    if len(words) != 2:
        await event.reply('Incorrect use of command.\nYou must provide url link to source which to follow\nFor example: /follow https://twitch.tv/kryabot')
        return

    parsed = urlparse(words[1])
    input_hostname = parsed.hostname

    # Remove www
    if input_hostname.startswith('www.'):
        input_hostname = input_hostname[4:]

    # Validate if allowed hostname
    if input_hostname not in FollowConfig.allowed_hostnames:
        await event.reply('Sorry, website <pre>{}</pre> is not supported!\n\nSupported websites: {}'.format(input_hostname, ', '.join(FollowConfig.allowed_hostnames)))
        return

    current_links = await event.client.db.getInfobotLinks(infobot['infobot_id'])
    if current_links and len(current_links) > 5:
        await event.reply('Cannot create new follow because already at limit of 5 follows.')
        return

    if input_hostname == FollowConfig.twitch_hostname:
        # Remove `/` from the beginning
        twitch_username = parsed.path[1:]
        twitch_user_request = await event.client.manager.api.twitch.get_users(usernames=[twitch_username])
        if 'data' not in twitch_user_request or len(twitch_user_request['data']) == 0:
            await event.reply('Twitch channel {} not found, initiated by {}'.format(twitch_username, event.message.text))
            return

        twitch_user = twitch_user_request['data'][0]
        user = await get_first(await event.client.db.getUserRecordByTwitchId(twitch_user['id']))
        if user is None:
            await event.client.db.createUserRecord(twitch_user['id'], twitch_user['login'], twitch_user['display_name'])
            user = await get_first(await event.client.db.getUserRecordByTwitchId(twitch_user['id']))

        if not user:
            event.client.logger.info('Failed to find kb user for Twitch ID {}, initiated by {}'.format(twitch_user['id'], event.message.text))
            return

        # Create profile in profile_twitch table if not created yet
        await event.client.db.registerTwitchProfile(user['user_id'])
        twitch_profile = await get_first(await event.client.db.getTwitchProfileByUserId(user['user_id']))
        if twitch_profile is None:
            event.client.logger.info('Failed to find profile_twitch record for user {}, initiated by {}'.format(user['user_id'], event.message.text))
            return

        # Check if already linked
        for current_link in current_links:
            if current_link['link_table'] == LinkTable.TWITCH.value and current_link['link_id'] == twitch_profile['profile_twitch_id']:
                await event.reply('This channel already followed!')
                return

        await event.client.db.createInfobotProfileLink(infobot['infobot_id'], LinkTable.TWITCH.value, twitch_profile['profile_twitch_id'])
        await event.client.manager.update(None, infobot_id=infobot['infobot_id'])
        await event.reply('Success!')
    elif input_hostname == FollowConfig.boosty_hostname:
        pass
    else:
        pass


@events.register(events.NewMessage(pattern='/following', func=lambda e: not e.is_private))
@required_admin()
@required_infobot()
async def command_show_following(event: events.NewMessage.Event, infobot):
    buttons = []
    for option in MenuButton.get_following_option_list():
        buttons.append(option)
    await event.reply('Please choose which follows you want to view:', buttons=buttons)


@events.register(events.CallbackQuery(pattern=MenuButton.BUTTON_SHOW_FOLLOWING.data, func=lambda e: not e.is_private))
@required_admin()
@required_infobot()
async def query_show_following(event: events.CallbackQuery.Event, infobot):
    buttons = []
    for option in MenuButton.get_following_option_list():
        buttons.append(option)

    await event.edit('Please choose which follows you want to view:', buttons=buttons)


@events.register(events.CallbackQuery(data=MenuButton.BUTTON_SHOW_FOLLOWING_TWITCH.data, func=lambda e: not e.is_private))
@required_admin()
@required_infobot()
async def query_show_following_twitch(event: events.CallbackQuery.Event, infobot):
    infobot_links = await event.client.db.getInfobotLinks(infobot['infobot_id'])
    if infobot_links is None or len(infobot_links) == 0:
        await event.edit('You do not have any registered Twitch follows, use command /follow to register one.', buttons=[MenuButton.BUTTON_SHOW_FOLLOWING])
        return

    reply_message = ''

    for link_table, link_rows in groupby(infobot_links, key=lambda x: x['link_table']):
        if link_table == LinkTable.TWITCH.value:
            reply_message += 'Twitch:\n'
            for row in link_rows:
                reply_message += '{}\n'.format(row['link_id'])
            reply_message += '\n'

    if reply_message == '':
        await event.edit('You do not have any Twitch.lv follows!', buttons=[MenuButton.BUTTON_SHOW_FOLLOWING])
        return

    await event.edit(reply_message, buttons=None)


@events.register(events.CallbackQuery(data=MenuButton.BUTTON_SHOW_FOLLOWING_BOOSTY.data, func=lambda e: not e.is_private))
@required_admin()
@required_infobot()
async def query_show_following_boosty(event: events.CallbackQuery.Event, infobot):
    infobot_links = await event.client.db.getInfobotLinks(infobot['infobot_id'])
    if infobot_links is None or len(infobot_links) == 0:
        await event.edit('You do not have any registered Twitch follows, use command /follow to register one.', buttons=[MenuButton.BUTTON_SHOW_FOLLOWING])
        return

    reply_message = ''

    for link_table, link_rows in groupby(infobot_links, key=lambda x: x['link_table']):
        if link_table == LinkTable.BOOSTY.value:
            reply_message += 'Boosty:\n'
            for row in link_rows:
                reply_message += '{}\n'.format(row['link_id'])
            reply_message += '\n'

    if reply_message == '':
        await event.edit('You do not have any Boosty.to follows!', buttons=[MenuButton.BUTTON_SHOW_FOLLOWING])
        return

    await event.edit(reply_message, buttons=None)
