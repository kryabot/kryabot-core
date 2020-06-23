TG_AUTH_CHAT = 'SELECT channel_subchat.global_events, channel_subchat.show_report, channel_subchat.on_refund, channel_subchat.min_sub_months, channel_subchat.refresh_status, channel_subchat.max_warns, channel_subchat.warn_mute_h, channel_subchat.warn_expires_in, channel_subchat.last_reminder, channel_subchat.reminder_cooldown, channel_subchat.getter_cooldown, channel_subchat.channel_subchat_id, channel_subchat.tg_chat_id, channel_subchat.auto_kick, channel.channel_id, user.tw_id, channel.channel_name, ac.token, ac.expires_at, ac.refresh_token, channel_subchat.enabled_join, channel_subchat.join_follower_only, channel_subchat.join_sub_only, channel_subchat.ban_time, channel_subchat.bot_lang, channel_subchat.join_link, channel_subchat.auto_mass_kick, channel_subchat.last_auto_kick, channel_subchat.on_stream, channel_subchat.welcome_message_id, user.user_id FROM channel_subchat INNER JOIN channel ON channel_subchat.channel_id=channel.channel_id INNER JOIN user on user.name = channel.channel_name INNER JOIN auth ac on ac.user_id = user.user_id where ac.type="BOT"'

async def getSql(sqlType):
    return {
        'create_channel': 'INSERT INTO channel (channel_name) VALUES (%s)',
        'find_channel': 'SELECT * FROM channel WHERE channel_name = %s',
        'create_user': 'INSERT INTO user (tw_id, name) VALUES (%s, %s)',
        'find_user_by_tw_id': 'SELECT * FROM user WHERE tw_id = %s',
        'update_user_admin': 'UPDATE user SET is_admin = %s WHERE user_id = %s',
        'find_admins': 'SELECT user.name FROM user WHERE user.is_admin = TRUE',
        'find_channel_admins': 'SELECT * FROM user_right WHERE admin = TRUE AND channel_id = %s',
        'add_user_right': 'INSERT INTO user_right (user_id, channel_id, admin, blacklisted) VALUES (%s, %s, %s, %s)',
        'update_user_right': 'UPDATE user_right SET admin = %s, blacklisted = %s WHERE user_id = %s AND chhannel_id = %s',
        'update_user_twitch_id': 'UPDATE user SET tw_id = %s WHERE user_id = %s',
        'find_user_right': 'SELECT admin, blacklisted FROM user_right WHERE channel_id = %s AND user_id = %s',
        'find_channel_notices': 'SELECT * FROM channel_notice',
        'find_auto_join': 'SELECT c.channel_id, c.channel_name, c.channel_name, c.command_symbol, c.default_notification, c.auto_join, c.trigger_period, u.user_id, u.name, u.dname, u.tw_id, u.is_admin FROM channel c JOIN user u on c.user_id = u.user_id WHERE auto_join = TRUE',
        'find_channel_commands': 'SELECT * FROM channel_command ORDER BY level DESC',
        'find_channel_commands_by_id': 'SELECT * FROM channel_command where channel_command.channel_id = %s ORDER BY level DESC',
        'find_notice_types': 'SELECT * FROM notice_type WHERE active = TRUE',
        'find_request_by_id': 'SELECT * FROM request WHERE request_id = %s',
        'find_request_by_user': 'SELECT * FROM request WHERE user_id = %s',
        'find_response_by_request': 'SELECT * FROM response WHERE request_id = %s',
        'find_response_by_chat_id': 'SELECT * FROM response WHERE tg_id = %s',
        'find_response_by_user_id': 'SELECT * FROM request join response on response.request_id = request.request_id where request.user_id = %s',
        'find_request_by_code': 'SELECT * FROM request WHERE code = %s',
        'find_subchat_link': 'SELECT * FROM channel_subchat WHERE channel_id = %s',
        'find_user_by_id': 'SELECT * FROM user WHERE user_id = %s',
        'find_all_link_channels': 'SELECT channel_subchat.tg_chat_id, channel.channel_id, channel.channel_name FROM channel_subchat INNER JOIN channel ON channel_subchat.channel_id=channel.channel_id;',
        'find_all_tg_channels_with_auth': TG_AUTH_CHAT + ';',
        'get_tg_chat_with_auth': TG_AUTH_CHAT + ' and channel_subchat.tg_chat_id = %s;',
        'add_request': 'INSERT INTO request (user_id, code) VALUES (%s, %s)',
        'add_response': 'INSERT INTO response (request_id, tg_id, tg_name, tg_second_name, tg_tag) VALUES (%s, %s, %s, %s, %s)',
        'add_request_link': 'INSERT INTO request_link (channel_id, user_id, link) VALUES (%s, %s, %s)',
        'get_settings': 'SELECT setting_key, setting_value FROM setting WHERE type = "BOT"',
        'save_bot_refresh_token': 'UPDATE auth SET auth.token = %s, auth.expires_at = CURRENT_TIMESTAMP + interval %s second, auth.refresh_token = %s where auth.type = "BOT" and auth.user_id = %s',
        'get_user_by_tg_id': 'select user.user_id, user.name, user.dname, user.tw_id, user.is_admin, user.supporter, user.soc_vk, user.soc_inst, user.soc_ut, user.allow_soc from user where user_id = (select request.user_id from request where request.request_id = (select response.request_id from response where response.tg_id = %s))',
        'save_chat_info_by_hash': 'UPDATE channel_subchat SET channel_subchat.tg_chat_id = %s, channel_subchat.tg_chat_name = %s WHERE channel_subchat.join_link like %s',
        'save_chat_info_after_join': 'UPDATE channel_subchat SET channel_subchat.tg_chat_id = %s, channel_subchat.tg_chat_name = %s, channel_subchat.join_link = %s WHERE channel_subchat.channel_subchat_id = %s',
        'delete_tg_members': 'DELETE FROM tg_group_member where tg_group_member.tg_chat_id = %s',
        'add_tg_member': 'INSERT INTO tg_group_member (tg_chat_id, tg_user_id, tg_first_name, tg_second_name, tg_username, sub_type) values (%s, %s, %s, %s, %s, %s)',
        'update_member_refresh_sta': 'UPDATE channel_subchat SET channel_subchat.refresh_status = %s, channel_subchat.last_member_refresh = CURRENT_TIMESTAMP where channel_subchat.tg_chat_id = %s',
        'update_auto_mass_kick_ts': 'UPDATE channel_subchat SET channel_subchat.last_auto_kick = %s where channel_subchat.channel_subchat_id = %s',
        'check_generated_id': 'select r.request_id from request r where r.code = %s and not exists(select 1 from response where response.request_id = r.request_id LIMIT 1)',
        'validate_web_token': 'CALL validateWebToken(%s)',
        'add_tg_ban_media': 'INSERT INTO tg_banned_media (channel_id, media_type, media_id, user_id, about) values (%s, %s, %s, %s, %s)',
        'get_banned_media': 'SELECT * FROM tg_banned_media',
        'get_user_rights_in_channel': 'SELECT * from tg_special_right sr where sr.channel_id = %s and sr.user_id = %s and sr.deleted = 0',
        'check_special_right_by_tg_user': 'SELECT * from tg_special_right where tg_special_right.tg_user_id = %s and tg_special_right.deleted = 0',
        'get_all_tg_special_rights': 'select * from tg_special_right where tg_special_right.deleted = 0',
        'get_tg_chat_rights': 'select * from tg_special_right where tg_special_right.deleted = 0 and tg_special_right.channel_id = %s',
        'add_special_right': 'INSERT into tg_special_right (channel_id, right_type, tg_user_id, user_first_name, user_last_name, username, by_tg_user_id) VALUES (%s, %s, %s, %s, %s, %s, %s)',
        'find_tg_user_by_twitch_name': 'select u.user_id, u.name, u.dname, u.tw_id, req.request_id, resp.tg_id, resp.tg_tag from user u join request req on req.user_id = u.user_id join response resp on resp.request_id = req.request_id where u.name = %s;',
        'create_notice': 'INSERT into twitch_chat_notice (channel_id, user_id, notice_type, tier, count1, count2, target_user_id) VALUES (%s, %s, %s, %s, %s, %s, %s)',
        'get_last_sub_info': 'select n.notice_type, n.tier, n.count1, n.count2 from twitch_chat_notice n where n.channel_id = %s and n.user_id = %s and (n.notice_type in ("sub", "resub", "subgift")) ORDER BY ts DESC limit 1;',
        'sp_saveTgSpecialRight': 'CALL saveTgSpecialRight(%s, %s, %s, %s, %s, %s, %s, %s, %s);',
        'sp_deleteTgSpecialRight': 'CALL deleteTgSpecialRight(%s, %s);',
        'get_resub_info': 'select n.notice_type, n.tier, n.count1, n.count2, n.ts from twitch_chat_notice n where n.channel_id = %s and n.user_id = %s and (n.notice_type in ("sub", "resub", "subgift")) ORDER BY ts DESC;',
        'get_subgift_info': 'select n.notice_type, n.tier, n.count1, n.count2, n.ts from twitch_chat_notice n where n.channel_id = %s and ((n.user_id = %s and n.notice_type = "submysterygift") OR (n.target_user_id = %s and n.notice_type = "subgift"))  ORDER BY ts DESC;',
        'update_tg_award': 'CALL updateTgAwardByUserId(%s, %s, %s, %s, %s)',
        'sp_getTgUserAwards': 'CALL getTgUserAwards(%s, %s)',
        'sp_updateUserTgAward': 'CALL updateUserTgAward(%s, %s, %s)',
        'get_tg_awards': 'CALL getTgAwardsByUserId(%s)',
        'sp_deleteTgAward': 'CALL deleteTgAwardByUserId(%s, %s, %s)',
        'set_getter': 'CALL setTgGetter(%s, %s, %s, %s, %s)',
        'get_getter': 'CALL getTgGetter(%s, %s)',
        'get_all_getters': 'CALL getAllTgGettersByUserId(%s)',
        'delete_getter': 'CALL deleteTgGetterByUserId(%s, %s, %s)',
        'mark_getter_broken': 'UPDATE tg_get SET tg_get.broken = 1 WHERE tg_get.tg_get_id = %s',
        'set_getter_cache_id': 'UPDATE tg_get SET tg_get.cache_message_id = %s WHERE tg_get.tg_get_id = %s',
        'sp_getRemindersByUserId': 'CALL getRemindersByUserId(%s)',
        'sp_saveReminderByUserId': 'CALL saveReminderByUserId(%s, %s, %s, %s, %s)',
        'sp_deleteReminderById': 'CALL deleteReminderById(%s, %s)',
        'sp_updateLastTgReminder': 'CALL updateLastTgReminder(%s)',
        'save_reminder_cooldown': 'UPDATE channel_subchat set channel_subchat.reminder_cooldown = %s where channel_subchat.channel_subchat_id = %s',
        'get_subchat_by_user': 'SELECT * FROM channel_subchat csc WHERE csc.channel_id = getChannelIdByUserId(%s)',
        'get_translations': 'SELECT lang, keyword, value FROM translation',
        'set_bot_lang': 'update channel_subchat set channel_subchat.bot_lang = %s where channel_subchat.channel_subchat_id = %s',
        'add_tg_word': 'INSERT INTO tg_word (channel_subchat_id, restrict_type_id, word, user_id) values (%s, %s, %s, %s)',
        'delete_tg_word': 'DELETE from tg_word where tg_word.channel_subchat_id = %s and tg_word.word = %s',
        'get_tg_words': 'SELECT * from tg_word',
        'get_linkage_date': 'SELECT request.request_id, response.response_id, request.user_id, response.tg_id, request.request_time, response.response_time from request left join response on response.request_id = request.request_id where request.user_id = (select user.user_id from user where user.tw_id = %s);',
        'sp_deleteTgLink': 'CALL deleteTgLink(%s)',
        'update_user_name': 'UPDATE user set user.name = %s, user.dname = %s where user.user_id = %s;',
        'set_subchat_mode': 'UPDATE channel_subchat SET channel_subchat.join_follower_only = %s, channel_subchat.join_sub_only = %s WHERE channel_subchat.tg_chat_id = %s',
        'set_subchat_entrance': 'UPDATE channel_subchat SET channel_subchat.enabled_join = %s WHERE channel_subchat.tg_chat_id = %s',
        'set_subchat_max_warns': 'UPDATE channel_subchat SET channel_subchat.max_warns = %s WHERE channel_subchat.tg_chat_id = %s',
        'set_subchat_warn_expire': 'UPDATE channel_subchat SET channel_subchat.warn_expire_in = %s WHERE channel_subchat.tg_chat_id = %s',
        'set_subchat_warn_mute_hours': 'UPDATE channel_subchat SET channel_subchat.warn_mute_h = %s WHERE channel_subchat.tg_chat_id = %s',
        'get_tg_chat_id_by_kb_user_id': 'SELECT channel_subchat.tg_chat_id FROM channel_subchat where channel_subchat.channel_id = getChannelIdByUserId(%s)',
        'get_tg_chat_id_by_channel_id': 'SELECT channel_subchat.tg_chat_id FROM channel_subchat where channel_subchat.channel_id = %s',
        'save_sub_event': 'INSERT INTO twitch_subdata (channel_id, user_id, event_id, event_type, event_ts, is_gift, tier, message) VALUES (%s, %s, %s, %s, %s, %s, %s, %s);',
        'get_bot_auth_by_user_id': 'SELECT * FROM auth WHERE auth.user_id = %s AND auth.type="BOT"',
        'get_all_bot_auths': 'SELECT a.auth_id, a.type, a.token, a.expires_at, a.refresh_token, a.scope, u.user_id, u.tw_id, u.name, u.dname FROM auth a left join user u on a.user_id = u.user_id WHERE a.type="BOT"',
        'get_twitch_subdata': 'SELECT * FROM twitch_subdata where twitch_subdata.twitch_subdata_id = %s',
        'set_subchat_action_on_refund': 'UPDATE channel_subchat SET channel_subchat.on_refund = %s where channel_subchat.tg_chat_id = %s',
        'set_subchat_action_on_stream': 'UPDATE channel_subchat SET channel_subchat.on_stream = %s where channel_subchat.tg_chat_id = %s',
        'set_welcome_message_id': 'UPDATE channel_subchat SET channel_subchat.welcome_message_id = %s where channel_subchat.tg_chat_id = %s',
        'set_user_soc_vk': 'UPDATE user SET user.soc_vk = %s where user.user_id = %s',
        'set_user_soc_inst': 'UPDATE user SET user.soc_inst = %s where user.user_id = %s',
        'set_user_soc_ut': 'UPDATE user SET user.soc_ut = %s where user.user_id = %s',
        'save_tg_stats': 'INSERT INTO stats_tg (channel_id, type, counter, when_dt) VALUES(%s, %s, %s, %s)',
        'update_broken_get': 'UPDATE tg_get SET tg_get.message_id = %s, tg_get.access_hash = %s, tg_get.file_ref = %s WHERE tg_get.channel_id = %s AND tg_get.keyword=%s',
        'update_kb_doc_sha': 'UPDATE tg_get SET tg_get.file_sha = %s WHERE tg_get.channel_id = %s AND tg_get.keyword=%s ',
        'set_subchat_mass_kick_period': 'UPDATE channel_subchat SET channel_subchat.auto_mass_kick = %s where channel_subchat.tg_chat_id = %s',
        'set_subchat_min_sub_months': 'UPDATE channel_subchat SET channel_subchat.min_sub_months = %s where channel_subchat.tg_chat_id = %s',
        'get_sub_history': 'SELECT * FROM twitch_subdata where channel_id = %s and user_id = %s ORDER BY event_ts DESC;',
        'get_sub_notice_history': 'SELECT * FROM twitch_chat_notice where channel_id = %s and user_id = %s and notice_type in ("sub", "resub", "subgift") ORDER BY ts DESC;',
        'get_tg_vote_active': 'SELECT * FROM tg_vote tgv where tgv.channel_id = %s and tgv.sta = 1',
        'create_tg_vote': 'INSERT INTO tg_vote (channel_id, description, created_by) VALUES (%s, %s, %s)',
        'finish_tg_vote': 'UPDATE tg_vote SET tg_vote.sta = 0 where tg_vote.tg_vote_id = %s',
        'tg_vote_nomination_access': 'UPDATE tg_vote SET tg_vote.open_nominations = %s WHERE tg_vote.tg_vote_id = %s',
        'add_tg_vote_nominate': 'CALL addTgVoteNominee(%s, %s, %s)',
        'add_tg_vote_ignore': 'CALL addTgVoteIgnore(%s, %s, %s)',
        'delete_tg_vote_nominee': 'CALL deleteTgVoteMember(%s, %s)',
        'add_tg_vote_point': 'CALL addTgVotePoint(%s, %s, %s)',
        'get_tg_vote_nominee_by_user': 'SELECT vn.tg_vote_nominee_id, u.name, u.dname, resp.tg_id, vn.tg_vote_id, vn.user_id, vn.type, vn.created_ts, vn.added_by, count(vp.tg_vote_nominee_id) as votes from tg_vote_nominee vn LEFT JOIN tg_vote_points vp on vn.tg_vote_nominee_id = vp.tg_vote_nominee_id left join user u on u.user_id = vn.user_id left join request req on req.user_id = u.user_id left join response resp on resp.request_id = req.request_id where vn.tg_vote_id = %s and vn.user_id = %s group by vn.tg_vote_nominee_id order by votes desc, vn.created_ts desc;',
        'get_tg_vote_nominees': 'SELECT vn.tg_vote_nominee_id, u.name, u.dname, resp.tg_id, vn.tg_vote_id, vn.user_id, vn.type, vn.created_ts, vn.added_by, count(vp.tg_vote_nominee_id) as votes from tg_vote_nominee vn LEFT JOIN tg_vote_points vp on vn.tg_vote_nominee_id = vp.tg_vote_nominee_id left join user u on u.user_id = vn.user_id left join request req on req.user_id = u.user_id left join response resp on resp.request_id = req.request_id where vn.tg_vote_id = %s group by vn.tg_vote_nominee_id order by votes desc, vn.created_ts desc;',
        'remove_sudo_right': 'UPDATE tg_special_right set tg_special_right.deleted = 1, tg_special_right.deleted_at = CURRENT_TIMESTAMP where tg_special_right.channel_id = %s and tg_special_right.tg_user_id = %s and tg_special_right.deleted = 0 and tg_special_right.right_type = "SUDO";',
        'update_subchat_report_visibility': 'UPDATE channel_subchat SET channel_subchat.show_report = %s WHERE channel_subchat.tg_chat_id = %s',
        'get_point_actions': 'SELECT * FROM channel_point_action',
        'get_point_actions_by_channel': 'SELECT * from channel_point_action where channel_point_action.channel_id = %s',
        'get_songs_all': 'SELECT * FROM song_source',
        'get_songs_by_channel': 'SELECT * FROM song_source where song_source.channel_id = %s',
        'get_channel_by_user_id': 'SELECT c.channel_id, c.user_id, c.channel_name, c.auto_join, c.allow_web_access, c.command_symbol, c.save_irc, c.trigger_period, cs.channel_subchat_id, u.tw_id FROM channel c LEFT JOIN user u ON u.user_id = c.user_id LEFT JOIN channel_subchat cs ON cs.channel_id = c.channel_id where c.user_id = %s;',
        'update_channel_global_events': 'UPDATE channel_subchat SET channel_subchat.global_events = %s WHERE channel_subchat.tg_chat_id = %s',
        'get_active_global_events': 'SELECT * FROM global_event ge WHERE ge.active_from < CURRENT_TIMESTAMP and (UNIX_TIMESTAMP(ge.active_to) = 0 or ge.active_to > CURRENT_TIMESTAMP );',
        'get_global_event_user_data_by_event': 'SELECT * from global_event_reward ger WHERE ger.global_event_id = %s and ger.user_id = %s',
        'set_global_event_user_reward': 'CALL setGlobalEventRewardForUser(%s, %s, %s, %s)',
        'get_global_user_awards': 'SELECT ger.amount, ger.val, ge.event_key, ge.label FROM global_event_reward ger left JOIN global_event ge ON ge.global_event_id = ger.global_event_id WHERE ger.user_id = %s;',
        'update_command_usage': 'CALL updateCommandUsage(%s);',
        'get_all_active_info_bots': 'SELECT * FROM infobot WHERE infobot.target_id is not NULL;',
        'get_all_new_info_bots': 'SELECT * FROM infobot WHERE infobot.target_id is NULL;',
        'get_instagram_profiles': 'SELECT * FROM profile_instagram',
        'get_instagram_history': 'SELECT * FROM history_instagram ih ORDER BY ih.created_ts DESC',
        'get_all_info_bots_links': 'SELECT * FROM infobot_link',
        'update_info_target_data': 'UPDATE infobot ib SET ib.target_type = "TG", ib.target_name = %s, ib.target_id = %s, ib.join_data = %s WHERE ib.infobot_id = %s',
        'get_infobot_by_user': 'SELECT * FROM infobot WHERE infobot.user_id = %s',
        'save_instagram_event': 'INSERT INTO history_instagram (data_type, profile_instagram_id, media_id, object_date) VALUES (%s, %s, %s, %s)',
        'get_all_twitch_profiles': 'SELECT pt.profile_twitch_id, pt.user_id, u.tw_id, u.name, u.dname FROM profile_twitch pt LEFT JOIN user u on pt.user_id = u.user_id;',
        'get_all_twitch_history': 'SELECT * FROM history_twitch ht WHERE ht.create_ts >  NOW() - INTERVAL 1 WEEK;',
        'get_boosty_profiles': 'SELECT * FROM profile_boosty',
        'get_boosty_history': 'SELECT * FROM history_boosty hb ORDER BY hb.created_ts DESC',
        'save_boosty_event': 'INSERT INTO history_boosty (profile_boosty_id, publish_ts, post_id) VALUES (%s, %s, %s)',
        'create_message': 'INSERT INTO twitch_message (channel_id, user_id, message) VALUES (%s, %s, %s)',
        'save_mass_ban': 'INSERT INTO twitch_mass_ban (channel_id, by_user_id, ban_text, ban_time, banned_count) VALUES (%s, %s, %s, %s, %s)',
        'wipe_twitch_messages': 'DELETE FROM twitch_message where twitch_message.created_at < NOW() - INTERVAL 1 DAY;',
        'search_twitch_messages': 'SELECT user.user_id, user.tw_id, user.name FROM twitch_message left join user on user.user_id = twitch_message.user_id where twitch_message.channel_id = %s and twitch_message.message LIKE %s group by user.user_id; ',
    }.get(sqlType, 'unknown_sql_type')
