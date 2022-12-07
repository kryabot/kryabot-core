from datetime import datetime

tg_prefix = 'tg.'
tw_prefix = 'tw.'
tw_api_prefix = tw_prefix + 'api.'

ttl_minute = 60
ttl_hour = ttl_minute * 60
ttl_half_day = ttl_hour * 12
ttl_day = ttl_hour * 24
ttl_week = ttl_day * 7
ttl_month = ttl_day * 30


def get_token_update_topic():
    return 'twitch_token_update'


def get_sync_topic():
    return 'sync_update'


def get_tg_auth_channel_key(tg_chat_id):
    return '{}auth_channel:{}'.format(tg_prefix, tg_chat_id)


def get_tw_channel_stream_flow(tw_id):
    return '{}stream_flow:{}'.format(tw_prefix, tw_id)


def get_tg_chat_rights(channel_id):
    return '{}chat_rights:{}'.format(tg_prefix, channel_id)


def get_kb_user(twitch_id):
    return '{}user:{}'.format(tw_prefix, twitch_id)


def get_kb_user_by_tg_id(tg_id):
    return '{}user:{}'.format(tg_prefix, tg_id)


def get_tg_cd_getter(tg_id):
    return '{}cd.getter:{}'.format(tg_prefix, tg_id)


def get_tg_cd_non_verified_list(tg_id):
    return '{}cd.non_verified:{}'.format(tg_prefix, tg_id)


def get_tg_channel_awards(channel_id):
    return '{}awards:{}'.format(tg_prefix, channel_id)


def get_api_tw_user_by_name(name):
    return '{}user_by_name:{}'.format(tw_api_prefix, name)


def get_chatters(name):
    return '{}chatters:{}'.format(tw_api_prefix, name)


def get_api_tw_user_by_id(twitch_id):
    return '{}user_by_id:{}'.format(tw_api_prefix, twitch_id)


def get_tg_cd_whoami(tg_chat_id, tg_user_id):
    return '{}cd.whoami:{}:{}'.format(tg_prefix, tg_chat_id, tg_user_id)


def get_tg_cd_inventory(tg_chat_id, tg_user_id):
    return '{}cd.inventory:{}:{}'.format(tg_prefix, tg_chat_id, tg_user_id)


def get_tg_cd_halloween_chestbox( tg_user_id):
    return '{}cd.halloween.chestbox:{}'.format(tg_prefix, tg_user_id)


def get_stats_tg_msg(tg_chat_id, n=None):
    if n is None:
        n = datetime.now()
    return 'tg.stats.msg:{}:{}'.format(tg_chat_id, '{}{}{}'.format(n.year, n.month, n.day))


def get_stats_tg_kick(tg_chat_id, n=None):
    if n is None:
        n = datetime.now()
    return 'tg.stats.kick:{}:{}'.format(tg_chat_id, '{}{}{}'.format(n.year, n.month, n.day))


def get_stats_tg_join(tg_chat_id, n=None):
    if n is None:
        n = datetime.now()
    return 'tg.stats.join:{}:{}'.format(tg_chat_id, '{}{}{}'.format(n.year, n.month, n.day))


def get_tw_sub_month(tw_chat_id, tw_user_id):
    return '{}submonth:{}:{}'.format(tw_prefix, tw_chat_id, tw_user_id)


def get_global_events():
    return 'tg.global.events'


def get_setting(key):
    return 'tg.setting.{}'.format(key)


def get_streams_data():
    return 'tg.streams.data'


def get_streams_forward_data():
    return 'tg.streamsforward.data'


def get_twitch_app_token():
    return 'twitch.app.token'


def get_twitch_game_info(id):
    return 'twitch.gameinfo.{}'.format(id)


def get_twitch_stream_cache(id):
    return 'twitch.stream.cache.{}'.format(id)


# All twitch received messages gets published here
def get_irc_topic_notice():
    return 'irc.request.notice'


def get_irc_topic_message():
    return 'irc.request.message'


def get_irc_topic_part():
    return 'irc.request.part'


# All responses (send message, mod acions, join, leave)
# def get_irc_response_topic():
#     return 'irc.request'

def get_pubsub_topic():
    return 'twitch.pubsub.incoming'

def get_error_queue():
    return 'report.error.queue'


def get_irc_response_queue():
    return 'irc.response.queue'


def get_telegram_group_size(tg_group_id):
    return 'tg.group.size.{}'.format(tg_group_id)


def get_general_ping(system: str):
    return 'general.ping.{}'.format(system)


def get_general_startup(system: str):
    return 'general.startup.{}'.format(system)


def get_halloween_update_topic():
    return 'globalevent.halloween.update'


def get_infobot_update_links_topic():
    return 'infobot.update_links'


def get_infobot_update_profile_topic():
    return 'infobot.update_profile'


def get_twitch_channel_update(twitch_id: int):
    return 'twitch.channel.update.{}'.format(twitch_id)


def get_infobot_target(tg_chat_id: int):
    return 'infobot.target.{}'.format(tg_chat_id)


def get_twitch_eventsub_queue() -> str:
    return 'twitch-event-sub-queue'


def get_tg_bot_requests() -> str:
    return 'tgbot.remote-requests'
