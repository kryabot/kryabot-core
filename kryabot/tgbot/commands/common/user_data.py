from dateutil.parser import parse
from datetime import datetime, timedelta
from utils.date_diff import get_datetime_diff_text
from utils.array import get_first


async def get_default_user_data():
    return {'twitch_user': None,
            'kb_user': None,
            'is_verified': False,
            'name': '',
            'display_name': '',
            'created_at': None,
            'tw_id': 0,
            'tg_id': 0,
            'kb_id': 0,
            'twitch_user_exists': False,
            'is_bot': False,

            'is_chat_owner': False,
            'bits': 0,
            'is_sub': False,
            'is_gifted': False,
            'sub_months': 0,
            'sub_tier': '',
            'gifted_subs': 0,
            'sub_ends_in': -1,

            'is_follower': False,
            'follow_date': None,
            'follow_text': '',

            'is_vip': False,
            'is_banned': False,
            'ban_comment': None,

            'has_awards': False,
            'awards': '',

            'is_admin': False,
            'is_sudo': False,
            'is_supporter': False,

            'allowed_soc': False,
            'soc_vk': '',
            'soc_inst': '',
            'soc_ut': '',

            'global_awards': None,
            'invitations': None,

            }


async def get_user_data(client, channel, user_id, skip_bits=True):
    user_data = await get_default_user_data()

    user_data['tg_id'] = user_id

    try:
        tg_user_entity = await client.get_entity(user_id)
        if tg_user_entity.bot:
            user_data['is_bot'] = True
    except Exception as ex:
        await client.exception_reporter(ex, 'get_u')

    target_user = await get_first(await client.db.getUserByTgChatId(user_id))
    user_data['kb_user'] = target_user

    # Basic info
    user_data = await fill_basic_info(user_data)
    user_data['global_awards'] = await client.db.getGlobalUserAwards(user_data['kb_id'])
    user_data['invitations'] = await client.db.getTgInvite(channel['channel_id'], user_data['kb_id'])

    # Chat related info
    user_data = await fill_chat_info(user_data, client, channel)
    # Twitch info
    user_data = await fill_twitch_info(user_data, client, channel)
    if skip_bits is False:
        user_data = await fill_bits_info(user_data, client, channel)

    return user_data


async def format_user_data(user_data, client, channel)->str:
    answer = ''
    lang = channel['bot_lang']

    if user_data['is_verified'] is False:
        answer = '⚠️<b>{}</b>⚠️'.format(client.get_translation(lang, 'USER_NOT_VERIFIED'))
    else:
        # Twitch name
        answer += '\n{}: <b>{}</b>'.format(client.get_translation(lang, 'USER_TWITCH_NAME'), user_data['display_name'])
        if user_data['is_chat_owner']:
            answer += ' 👑'

        if user_data['twitch_user_exists'] is False:
            answer += '\nWarning: user Twitch account does not exist anymore (Twitch ID {})'.format(user_data['tw_id'])
        else:
            if user_data['is_chat_owner'] is False:
                # Twitch sub data
                answer += '\n{} {}: '.format(await custom_subinfo_badge(channel['channel_id']), client.get_translation(lang, 'USER_SUB_INFO'))
                if user_data['is_sub'] is True:
                    if user_data['sub_months'] > 0:
                        answer += '{count} {text} {tier}'.format(count=user_data['sub_months'],
                                                                 text=client.get_translation(lang, 'USER_SUB_MONTHS'),
                                                                 tier=await map_sub_tier(user_data['sub_tier']))
                        if user_data['is_gifted']:
                            answer += ' 🎁'
                    else:
                        answer += client.get_translation(lang, 'USER_SUB')
                elif user_data['is_sub'] is False:
                    answer += '<b>{}</b>'.format(client.get_translation(lang, 'USER_NOT_SUB'))
                else:
                    # None
                    pass

                # Twitch follow info
                if user_data['is_follower']:
                    answer += '\n\n{} {} ({})'.format(client.get_translation(lang, 'USER_FOLLOWING'), user_data['follow_text'], user_data['follow_date'])

            if user_data['gifted_subs'] > 0:
                answer += '\n{}: {} 🔦'.format(client.get_translation(lang, 'USER_GIFTED_SUBS'), user_data['gifted_subs'])

        if user_data['bits'] > 0:
            answer += '\n💎 <b>{}</b>'.format(user_data['bits'])

        if user_data['allowed_soc'] is True:
            soc_data = ''

            if user_data['soc_vk'] is not None and user_data['soc_vk'] != '':
                soc_data += '<a href="{url}">VK</a> '.format(url=user_data['soc_vk'])
            if user_data['soc_inst'] is not None and user_data['soc_inst'] != '':
                soc_data += '<a href="{url}">Instagram</a> '.format(url=user_data['soc_inst'])
            if user_data['soc_ut'] is not None and user_data['soc_ut'] != '':
                soc_data += '<a href="{url}">Youtube</a> '.format(url=user_data['soc_ut'])

            if soc_data is not None and soc_data != '':
                answer += '\n\n' + soc_data

        # Award list
        if user_data['has_awards'] is True:
            answer += '\n\n<b>{}:</b>{}\n'.format(client.get_translation(lang, 'USER_AWARDS'), user_data['awards'])

        global_awards = ''
        for global_award in user_data['global_awards']:
            global_awards += client.get_translation(lang, global_award['label']).format(amt=global_award['amount'], val=global_award['val'])

        if len(global_awards) > 0:
            answer += '\n\n<b>{}</b>\n{}\n'.format(client.get_translation(lang, 'USER_GLOBAL_AWARDS'), global_awards)

    if user_data['is_admin'] is True:
        answer += '\n⚙️ <b>Dev</b>'

    if user_data['is_supporter'] is True:
        answer += '\n⚜️ <b>Supporter</b>'

    if user_data['is_sudo'] is True:
        answer += '\n⛩ <b>SUDO</b>'

    # Whitelist/blacklist
    if user_data['is_vip'] is True:
        answer += '\n⭐️ <b>{}</b>'.format(client.get_translation(lang, 'USER_RIGHT_WL'))
    if user_data['is_banned'] is True:
        answer += '\n❌ <b>{}</b>'.format(client.get_translation(lang, 'USER_RIGHT_BL'))
        if user_data['ban_comment'] is not None and len(user_data['ban_comment']) > 0:
            answer += '\n\n<pre>{}</pre>'.format(user_data['ban_comment'])

    # Invitation data
    if user_data['invitations']:
        inviter = user_data['invitations'][0]['dname'] if user_data['invitations'][0]['dname'] else user_data['invitations'][0]['name']
        answer += '\n\n🎟 {}'.format(client.get_translation(lang, 'USER_INVITED_BY').format(inviter))

    return answer


async def fill_basic_info(user_data):
    if user_data['kb_user'] is None or user_data['kb_user'] is [] or user_data['kb_user'] is {}:
        return user_data

    if not ('tw_id' in user_data['kb_user']):
        return user_data

    user_data['is_verified'] = True
    user_data['name'] = user_data['kb_user']['name']
    user_data['display_name'] = user_data['kb_user']['dname']
    user_data['tw_id'] = user_data['kb_user']['tw_id']
    user_data['kb_id'] = user_data['kb_user']['user_id']
    user_data['is_admin'] = bool(user_data['kb_user']['is_admin'])
    user_data['is_supporter'] = bool(user_data['kb_user']['supporter'])
    user_data['allowed_soc'] = bool(user_data['kb_user']['allow_soc'])
    user_data['soc_vk'] = user_data['kb_user']['soc_vk']
    user_data['soc_inst'] = user_data['kb_user']['soc_inst']
    user_data['soc_ut'] = user_data['kb_user']['soc_ut']

    return user_data


async def fill_twitch_info(user_data, client, channel):
    if user_data['is_verified'] is False:
        return user_data

    user_data = await fill_twitch_user_info(user_data, client)

    # Chat owners can not follow or sub themselfs
    if not user_data['is_chat_owner'] and user_data['is_verified'] and user_data['twitch_user_exists']:
        user_data = await fill_twitch_follow_info(user_data, client, channel)
        user_data = await fill_twitch_sub_info(user_data, client, channel)

    return user_data


async def fill_twitch_user_info(user_data, client):
    try:
        twitch_user = await client.api.twitch.get_users(ids=[user_data['tw_id']])
        twitch_user = twitch_user['data'][0]

        if user_data['display_name'] != twitch_user['display_name'] or user_data['name'] != twitch_user['login']:
            client.logger.info('[{}] Changing from [{} {}] to [{} {}]'.format(user_data['tw_id'], user_data['name'], user_data['display_name'], twitch_user['login'], twitch_user['display_name']))
            await client.db.updateUserTwitchName(user_data['kb_id'], twitch_user['login'], twitch_user['display_name'], tg_user_id=user_data['tg_id'], tw_user_id=user_data['tw_id'])

        user_data['twitch_user'] = twitch_user
        user_data['name'] = twitch_user['login']
        user_data['display_name'] = twitch_user['display_name']
        user_data['created_at'] = twitch_user['created_at']
        user_data['twitch_user_exists'] = True
    except Exception as err:
        await client.exception_reporter(err, 'Twitch ID: {}'.format(user_data['tw_id']))
        user_data['twitch_user_exists'] = False

    return user_data


async def fill_twitch_follow_info(user_data, client, channel):
    try:
        follow_info = await client.api.twitch.check_channel_following(channel['tw_id'], user_data['tw_id'])
        created_dt = parse(follow_info['created_at'].replace('Z', ''))
        dt_diff = datetime.utcnow() - created_dt
        if dt_diff.seconds > 0:
            user_data['is_follower'] = True
            user_data['follow_date'] = follow_info['created_at'].split('T')[0]
            user_data['follow_text'] = await get_datetime_diff_text(datetime.utcnow(), created_dt)
    except Exception as err:
        if '404' in str(err):
            # 404 means user is not Twitch follower
            pass
        else:
            await client.exception_reporter(err, 'Checking follow info of user {} in channel {}'.format(user_data['tw_id'], channel['tw_id']))
    return user_data


async def fill_twitch_sub_info(user_data, client, channel):
    # Refreshed token for sub checking if expired token
    sub, sub_data, sub_error = await client.api.is_sub_v3(channel, user_data['kb_user'], client.db)
    if sub is True:
        user_data['is_sub'] = True

        sub_info = await get_first(await client.db.getLastSubHistoricalInfo(channel['channel_id'], user_data['kb_id']))
        if sub_info is not None:
            months = sub_info['count1']
            if months == 0:
                sub_recs = await client.db.getResubHistory(channel['channel_id'], user_data['kb_id'])
                i = 0
                for sub_rec in sub_recs:
                    if sub_rec['count1'] == 0:
                        i += 1
                    if sub_rec['count1'] > 0:
                        months = sub_rec['count1'] + i
                        break

                if months == 0:
                    months += i

            user_data['sub_months'] = months
            user_data['sub_tier'] = sub_data['sub_plan']
            user_data['is_gifted'] = sub_info['notice_type'] == 'subgift'

        sub_months_cache = await client.db.get_twitch_sub_count_from_cache(channel['tw_id'], user_data['tw_id'])
        if sub_months_cache is not None:
            if not isinstance(sub_months_cache, int):
                sub_months_cache = int(sub_months_cache)
            if sub_months_cache > user_data['sub_months']:
                user_data['sub_months'] = sub_months_cache

    subgift_history = await client.db.getSubgiftHistory(channel['channel_id'], user_data['kb_id'])
    if subgift_history:
        for history in subgift_history:
            if history['count2'] > 0:
                user_data['gifted_subs'] = history['count2']
                break

    return user_data


async def fill_chat_info(user_data, client, channel):
    if user_data['is_verified'] is False:
        return user_data

    if channel['tw_id'] == user_data['tw_id']:
        user_data['is_chat_owner'] = True

    # Awards
    user_awards = await client.db.getUserTgAwards(channel['channel_name'], user_data['tg_id'])
    award_text = ''
    for award in user_awards:
        if award['counter'] > 0:
            user_data['has_awards'] = True
            award_text += '\n' + award['award_template'].format(counter=award['counter'])

    user_data['awards'] = award_text

    # Vip or Banned status
    user_data['is_vip'], user_data['is_banned'], user_data['ban_comment'] = await client.has_special_rights(user_data['kb_id'], user_data['tg_id'], channel)
    user_data['is_sudo'] = await client.is_chatsudo(user_data['kb_id'], user_data['tg_id'], channel)
    return user_data


async def fill_bits_info(user_data, client, channel):
    try:
        bits_data = await client.api.twitch.get_total_bits_by_user(channel['tw_id'], user_data['tw_id'], channel['token'])
    except Exception as err:
        await client.exception_reporter(err, 'fill_bits_info')
        return user_data

    bits_data = bits_data['data']
    if len(bits_data) > 0:
        user_data['bits'] = bits_data[0]['score']

    return user_data


async def map_sub_tier(plan_code):
    plan_code = '' + str(plan_code)

    if plan_code == '1000':
        return '[ T1 ]'
    if plan_code == '2000':
        return '[ T2 ]'
    if plan_code == '3000':
        return '[ T3 ]'
    if plan_code.lower() == 'prime':
        return '[ TP ]'

    return ''


async def custom_subinfo_badge(channel_id):
    return {4: '💩',
            5: '🐸',
            6: '🦆',
            12: '🥨',
            17: '🔥',
            24: '🎮',
            31: '🦖',
            34: '🐝',
            36: '🐹',
            40: '🦉',
            41: '🐧',
            51: '🦊',
            64: '🥢',
            }.get(channel_id, '🎖')

