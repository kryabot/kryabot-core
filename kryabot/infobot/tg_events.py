import enum
from typing import List

from telethon import events, Button
from urllib.parse import urlparse

from infobot import UpdateBuilder
from infobot.tg_event_helpers import required_admin, required_infobot, required_infobot_link
from object.Translator import Translator
from utils import redis_key
from utils.array import get_first
from infobot.LinkTable import LinkTable
from infobot.Target import Target
from infobot.TargetLink import TargetLink, TwitchLinkConfig


class FollowConfig:
    twitch_hostname = 'twitch.tv'
    boosty_hostname = 'boosty.to'
    allowed_hostnames = [twitch_hostname]


class MenuButton(enum.Enum):
    BUTTON_SHOW_FOLLOWING_LIST = 'menufollowlist:{}'
    BUTTON_SHOW_FOLLOWING = 'menushowfollowsoptions'
    BUTTON_FOLLOW_SELECT = 'menufollowselect:{}:{}'
    BUTTON_FOLLOW_DELETE = 'menufollowdelete:{}:{}'
    BUTTON_FOLLOW_CONFIG = 'menufollowconfig:{}:{}'
    BUTTON_FOLLOW_CONFIG_EDIT = 'menufollowcfgedit:{}:{}:{}'
    BUTTON_CLOSE = 'close'

    @staticmethod
    def get_available_platforms() -> List[Button]:
        default_data = MenuButton.BUTTON_SHOW_FOLLOWING_LIST.data

        twitch_button = Button.inline(text=FollowConfig.twitch_hostname.upper(), data=default_data.format(LinkTable.TWITCH.value))
        boosty_button = Button.inline(text=FollowConfig.boosty_hostname.upper(), data=default_data.format(LinkTable.BOOSTY.value))

        return [twitch_button, boosty_button]

    def translated(self, lang: str = 'en'):
        return Button.inline(text=Translator.getInstance().getLangTranslation(lang, self.translator_key), data=self.data)

    @property
    def data(self) -> str:
        return self.value

    @property
    def translator_key(self) -> str:
        return 'IB_' + self.name


def register_events(client):
    # For test/debug
    client.add_event_handler(pong, events.NewMessage(pattern='^/ping$'))
    # client.add_event_handler(debug_query, events.CallbackQuery())

    # Usages
    client.add_event_handler(command_follow, events.NewMessage(pattern='^/(follow|follow@{})( .*|$)'.format(client.me.username), func=lambda e: not e.is_private))
    client.add_event_handler(command_show_following, events.NewMessage(pattern="^/following($|@{}$)".format(client.me.username), func=lambda e: not e.is_private))
    client.add_event_handler(query_show_following_list, events.CallbackQuery(pattern=MenuButton.BUTTON_SHOW_FOLLOWING_LIST.data.format('*'), func=lambda e: not e.is_private))
    client.add_event_handler(query_show_following, events.CallbackQuery(data=MenuButton.BUTTON_SHOW_FOLLOWING.data, func=lambda e: not e.is_private))
    client.add_event_handler(query_close, events.CallbackQuery(data=MenuButton.BUTTON_CLOSE.data, func=lambda e: not e.is_private))
    client.add_event_handler(query_select_link, events.CallbackQuery(pattern=MenuButton.BUTTON_FOLLOW_SELECT.data.format('*', '*'), func=lambda e: not e.is_private))
    client.add_event_handler(query_link_delete, events.CallbackQuery(pattern=MenuButton.BUTTON_FOLLOW_DELETE.data.format('*', '*'), func=lambda e: not e.is_private))
    client.add_event_handler(query_link_config_update, events.CallbackQuery(pattern=MenuButton.BUTTON_FOLLOW_CONFIG_EDIT.data.format('*', '*', '*'), func=lambda e: not e.is_private))


async def pong(event):
    await event.reply('pong')


async def debug_query(event):
    print(event.query.data)


@required_admin()
@required_infobot()
async def command_follow(event: events.NewMessage.Event, infobot: Target):
    bad_usage_text = 'Incorrect use of command.\nYou must provide url link to source which to follow!\nFor example: /follow https://twitch.tv/kryabot'
    words = event.raw_text.split(' ')
    if len(words) != 2:
        await event.reply(bad_usage_text, link_preview=False)
        return

    parsed = urlparse(words[1])
    input_hostname = parsed.hostname
    if input_hostname is None:
        await event.reply(bad_usage_text, link_preview=False)
        return

    # Remove www
    if input_hostname.startswith('www.'):
        input_hostname = input_hostname[4:]

    # Validate if allowed hostname
    if input_hostname not in FollowConfig.allowed_hostnames:
        await event.reply('Sorry, website <pre>{}</pre> is not supported!\n\nSupported websites: {}'.format(input_hostname, ', '.join(FollowConfig.allowed_hostnames)))
        return

    if input_hostname == FollowConfig.twitch_hostname:
        current_links = await event.client.db.getInfobotLinksByType(infobot.id, LinkTable.TWITCH.value)
        if current_links and len(current_links) >= 3:
            await event.reply('You cannot add new Twitch channel because you reached limit of 3 channels.')
            return

        # Remove `/` from the beginning
        twitch_username = parsed.path[1:]

        twitch_user_request = await event.client.manager.api.twitch.get_users(usernames=[twitch_username])
        if 'data' not in twitch_user_request or len(twitch_user_request['data']) == 0:
            await event.reply('Twitch channel {} not found, initiated by {}'.format(twitch_username, event.message.text))
            return

        twitch_user = twitch_user_request['data'][0]
        user = await get_first(await event.client.db.getUserRecordByTwitchId(int(twitch_user['id']), skip_cache=True))
        if user is None:
            await event.client.db.createUserRecord(int(twitch_user['id']), twitch_user['login'], twitch_user['display_name'])
            user = await get_first(await event.client.db.getUserRecordByTwitchId(int(twitch_user['id'])))

        if not user:
            event.client.logger.info('Failed to find kb user for Twitch ID {}, initiated by {}'.format(twitch_user['id'], event.message.text))
            return

        # Create profile in profile_twitch table if not created yet
        await event.client.db.registerTwitchProfile(user['user_id'])
        message = UpdateBuilder.TwitchUpdate(UpdateBuilder.UpdateAction.UPDATE, user['user_id'])
        await event.client.db.redis.publish_event(redis_key.get_infobot_update_profile_topic(), message.to_json())

        twitch_profile = await get_first(await event.client.db.getTwitchProfileByUserId(user['user_id']))
        if twitch_profile is None:
            event.client.logger.info('Failed to find profile_twitch record for user {}, initiated by {}'.format(user['user_id'], event.message.text))
            return

        # Check if already linked
        if current_links:
            for current_link in current_links:
                if current_link['link_table'] == LinkTable.TWITCH.value and current_link['link_id'] == twitch_profile['profile_twitch_id']:
                    await event.reply('This channel already followed!')
                    return

        await event.client.db.createInfobotProfileLink(infobot.id, LinkTable.TWITCH.value, twitch_profile['profile_twitch_id'])
        await event.client.db.saveInfoBotLinkConfig(infobot.id, LinkTable.TWITCH.value, twitch_profile['profile_twitch_id'], TwitchLinkConfig({}).export())
        await event.reply('Success!')

        message = UpdateBuilder.LinkUpdate(UpdateBuilder.UpdateAction.UPDATE, infobot.id, LinkTable.TWITCH.value, 0)
        await event.client.db.redis.publish_event(redis_key.get_infobot_update_links_topic(), message.to_json())
    elif input_hostname == FollowConfig.boosty_hostname:
        await event.reply('Sorry, new boosty follows currently are not allowed!')
    else:
        event.client.logger.info('Unhandled hostname: {}'.format(event.raw_text))


@required_admin()
@required_infobot()
async def command_show_following(event: events.NewMessage.Event, infobot: Target):
    buttons = []
    for option in MenuButton.get_available_platforms():
        buttons.append([option])

    buttons.append([MenuButton.BUTTON_CLOSE.translated(infobot.get_lang())])
    await event.reply(event.client.translator.getLangTranslation(infobot.get_lang(), 'IB_VIEW_FOLLOW_SELECT_PLATFORM'), buttons=buttons)


@required_admin()
@required_infobot()
async def query_show_following(event: events.CallbackQuery.Event, infobot: Target):
    buttons = []
    for option in MenuButton.get_available_platforms():
        buttons.append([option])

    buttons.append([MenuButton.BUTTON_CLOSE.translated(infobot.get_lang())])
    await event.edit(event.client.translator.getLangTranslation(infobot.get_lang(), 'IB_VIEW_FOLLOW_SELECT_PLATFORM'), buttons=buttons)


@required_admin()
async def query_close(event: events.CallbackQuery.Event):
    await event.delete()


@required_admin()
@required_infobot()
@required_infobot_link()
async def query_show_following_list(event: events.CallbackQuery.Event, infobot: Target):
    parts = event.query.data.decode().split(':')
    platform: str = parts[1]

    buttons = []
    if infobot.selected_links:
        for link in infobot.selected_links:
            buttons.append([Button.inline(text=link.get_display_button(), data=MenuButton.BUTTON_FOLLOW_SELECT.data.format(LinkTable.TWITCH.value, link.link_id))])

        reply_message = event.client.translator.getLangTranslation(infobot.get_lang(), 'IB_VIEW_FOLLOW_LIST_{}'.format(platform.upper()))
    else:
        reply_message = event.client.translator.getLangTranslation(infobot.get_lang(), 'IB_VIEW_FOLLOW_EMPTY_{}'.format(platform.upper()))

    buttons.append([MenuButton.BUTTON_SHOW_FOLLOWING.translated(infobot.get_lang())])
    await event.edit(reply_message, buttons=buttons)


@required_admin()
@required_infobot()
@required_infobot_link()
async def query_select_link(event: events.CallbackQuery.Event, infobot: Target):
    link: TargetLink = infobot.get_selected_link()
    buttons = []
    cfg_text = ''

    option_enabled = event.client.translator.getLangTranslation(infobot.get_lang(), 'IB_FOLLOW_OPTION_ENABLED')
    option_disabled = event.client.translator.getLangTranslation(infobot.get_lang(), 'IB_FOLLOW_OPTION_DISABLED')
    for field_name in link.config.fields.keys():
        keyword = 'IB_BUTTON_FOLLOW_CONFIG_EDIT_{}'.format(str(field_name).upper())
        current_value = option_enabled if link.config.get_field_value(field_name) else option_disabled
        cfg_text += '🔸 {}\n'.format(event.client.translator.getLangTranslation(infobot.get_lang(), keyword).format(current_value))
        text = event.client.translator.getLangTranslation(infobot.get_lang(), keyword).format(option_disabled if link.config.get_field_value(field_name) else option_enabled)
        buttons.append([Button.inline(text='⚙️' + text, data=MenuButton.BUTTON_FOLLOW_CONFIG_EDIT.data.format(link.get_table(), link.link_id, field_name))])

    delete_button = MenuButton.BUTTON_FOLLOW_DELETE.translated(infobot.get_lang())
    delete_button.data = (delete_button.data.decode().format(link.get_table(), link.link_id)).encode()
    delete_button.text = '❌ ' + delete_button.text
    buttons.append([delete_button])
    buttons.append([MenuButton.BUTTON_SHOW_FOLLOWING.translated(infobot.get_lang())])
    buttons.append([MenuButton.BUTTON_CLOSE.translated(infobot.get_lang())])

    text = event.client.translator.getLangTranslation(infobot.get_lang(), 'IB_VIEW_FOLLOW_SELECTED').format(link.get_display_text())
    if len(cfg_text) > 0:
        text += '\n\n' + cfg_text
    await event.edit(text, buttons=buttons)


@required_admin()
@required_infobot()
@required_infobot_link()
async def query_link_delete(event: events.CallbackQuery.Event, infobot: Target):
    link: TargetLink = infobot.get_selected_link()
    await event.client.db.deleteInfoBotLink(infobot.id, link.get_table(), link.link_id)
    buttons = [[MenuButton.BUTTON_SHOW_FOLLOWING.translated(infobot.get_lang())],
               [MenuButton.BUTTON_CLOSE.translated(infobot.get_lang())]]

    text = event.client.translator.getLangTranslation(infobot.get_lang(), 'IB_VIEW_FOLLOW_REMOVED').format(link.get_display_text())
    await event.edit(text, buttons=buttons)

    # Publish changes
    message = UpdateBuilder.LinkUpdate(UpdateBuilder.UpdateAction.REMOVE, infobot.id, link.get_table(), link.link_id)
    await event.client.db.redis.publish_event(redis_key.get_infobot_update_links_topic(), message.to_json())


@required_admin()
@required_infobot()
@required_infobot_link()
async def query_link_config_update(event: events.CallbackQuery.Event, infobot: Target):
    link: TargetLink = infobot.get_selected_link()
    parts = event.query.data.decode().split(':')

    # Reverse bool value
    new_value = not link.config.get_field_value(parts[3])
    link.config.set_field(field_name=parts[3], field_value=new_value)
    await event.client.db.saveInfoBotLinkConfig(infobot.id, link.get_table(), link.link_id, link.config.export())
    await query_select_link(event)

    # Publish changes
    message = UpdateBuilder.LinkUpdate(UpdateBuilder.UpdateAction.UPDATE, infobot.id, link.get_table(), link.link_id)
    await event.client.db.redis.publish_event(redis_key.get_infobot_update_links_topic(), message.to_json())
