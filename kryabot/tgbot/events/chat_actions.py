from telethon.tl.types import PeerUser

from tgbot.events.global_events.GlobalEventFactory import GlobalEventFactory
from tgbot.events.utils import is_valid_channel
from utils.formatting import format_html_user_mention
from tgbot.commands.common.user_data import get_user_data, format_user_data
from telethon.utils import get_peer_id
from utils.constants import TG_TEST_GROUP_ID
from utils.array import get_first


async def user_join_check(client, channel, tg_entity, message_id=0):
    await client.db.update_tg_stats_join(channel['tg_chat_id'])

    if channel['auth_status'] == 0:
        await client.send_message(client.get_translation(channel['bot_lang'], 'GENERAL_MISSING_AUTH'))
        return

    try:
        data = await get_user_data(client, channel, tg_entity)
        text = await format_user_data(data, client, channel)

        need_kick = await is_kickable(data, channel)

        if data['invitations']:
            try:
                await client.db.markInvitationUsed(channel['channel_id'], data['kb_id'])
            except Exception as ex:
                client.logger.error(ex)

        if need_kick:
            if channel['auto_kick'] == 1:
                try:
                    await client.kick_user_from_channel(channel['tg_chat_id'], tg_entity.id, channel['ban_time'])
                    text += '\n\n' + client.get_translation(channel['bot_lang'], 'JOIN_KICKED')
                except:
                    text += '\n\n' + client.get_translation(channel['bot_lang'], 'JOIN_KICK_FAILED')

            else:
                text += '\n\n' + client.get_translation(channel['bot_lang'], 'JOIN_AUTO_KICK_DISABLED')

        if message_id > 0:
            await client.send_message(channel['tg_chat_id'], text, reply_to=message_id, link_preview=False)
        else:
            await client.send_message(channel['tg_chat_id'], text, link_preview=False)

        if not need_kick:
            # If welcome message is set and exists, send it, else send guard sticker as default
            if channel['welcome_message_id'] > 0:
                try:
                    welcome_message = await client.get_messages(channel['tg_chat_id'], ids=channel['welcome_message_id'])
                    new_welcome_message = await client.send_message(channel['tg_chat_id'], welcome_message)
                    if new_welcome_message:
                        await client.db.setWelcomeMessageId(channel['tg_chat_id'], new_welcome_message.id)
                except ValueError:
                    await client.send_krya_guard_sticker(channel['tg_chat_id'])
                    await client.db.setWelcomeMessageId(channel['tg_chat_id'], 0)
                except Exception as wex:
                    await client.exception_reporter(wex, 'Channel join: {} -> {}'.format(tg_entity.id, channel['channel_name']))
            else:
                await client.send_krya_guard_sticker(channel['tg_chat_id'])
        elif channel['auto_kick'] == 1:
            await client.send_krya_kill_sticker(channel['tg_chat_id'])

    except Exception as err:
        await client.exception_reporter(err, 'Channel join: {} -> {}'.format(tg_entity.id, channel['channel_name']))


async def user_left(client, channel, tg_user_id):
    if not is_valid_channel(channel):
        return

    user_entity = await client.get_entity(PeerUser(int(tg_user_id)))
    user_mention = await format_html_user_mention(user_entity)

    await client.send_message(channel['tg_chat_id'], client.get_translation(channel['bot_lang'], 'CHAT_ACTION_USER_LEFT').format(user=user_mention))


async def is_kickable(user_data, channel):
    if user_data['is_admin'] is True:
        return False

    # Allow linked twitch channel owner
    if user_data['is_chat_owner'] is True:
        return False

    # Allowed to add bots anytime
    if user_data['is_bot'] is True:
        return False

    # Add vips without checking other stats
    if user_data['is_vip'] is True:
        return False

    # User was manually invited via twitch command, allow access
    if user_data['invitations'] and len(user_data['invitations']) > 0:
        return False

    # If entrance is closed, no user can join
    if channel['enabled_join'] == 0:
        return True

    # Access is restricted if user is not verified in bot system
    if user_data['is_verified'] is False:
        return True

    # Access is restricted is user was blacklisted
    if user_data['is_banned'] is True:
        return True

    # Access is restricted if follow is needed and user is not follower
    if channel['join_follower_only'] == 1 and user_data['is_follower'] is False:
        return True

    # Access is restricted if subscribtion is needed and user is not subscriber
    if channel['join_sub_only'] == 1 and user_data['is_sub'] is False:
        return True

    # If enabled minimum sub month limiter, check sub months
    if channel['join_sub_only'] == 1 and channel['min_sub_months'] > 0 and user_data['is_sub'] is True and channel['min_sub_months'] > user_data['sub_months']:
        return True

    return False

async def process_bot_chat(event):
    if not event.mentioned:
        return

    if not event.message.text:
        text = 'мне кажется я тупой'
    else:
        text = event.message.text

    chat_id: int = int(get_peer_id(event.message.peer_id, add_mark=False))
    user_id: int = event.message.sender_id
    user = await get_first(await event.client.db.getUserByTgChatId(user_id))
    if not user:
        return

    channel = await get_first(await event.client.db.get_auth_subchat(chat_id))
    if not channel:
        return

    if GlobalEventFactory.is_in_use(chat_id):
        return

    if chat_id != TG_TEST_GROUP_ID and not bool(user['supporter']) and not channel['tw_id'] == user['tw_id']:
        return

    if '@twitchkryabot' in text.lower():
        text = text.replace('@twitchkryabot', '')

    resp = await event.client.api.yandex.do_yalm_bot_query(text, user_id)
    if resp and 'text' in resp:
        filtered = filter(lambda word: not str(word).startswith('@'), resp['text'].split(' '))
        await event.reply(' '.join(filtered))
