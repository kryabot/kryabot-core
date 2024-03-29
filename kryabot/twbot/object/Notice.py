

class Notice:

    def __init__(self, data):
        self.raw_tags = data

        self.badges = None
        self.display_name = None
        self.color = None
        self.flags = None
        self.emotes = None
        self.id = None
        self.login = None
        self.mod = None

        self.msg_id = None
        self.msg_param_mass_gift_count = None
        self.msg_param_sender_count = None
        self.msg_param_sub_plan = None
        self.msg_param_sub_plan_name = None
        self.msg_param_cumulative_months = None
        self.msg_param_months = None
        self.msg_param_should_share_streak = None
        self.msg_param_origin_id = None
        self.msg_param_recipient_display_name = None
        self.msg_param_recipient_id = None
        self.msg_param_recipient_user_name = None
        self.msg_param_fun_string = None
        self.msg_param_promo_gift_total = None
        self.msg_param_promo_name = None
        self.msg_param_viewer_count = None
        self.msg_param_streak_months = None
        self.msg_param_sender_login = None
        self.msg_param_sender_name = None
        self.msg_param_profile_image_url = None
        # {"badge-info": "subscriber/2", "badges": "subscriber/0", "color": "", "display-name": "soldierghost", "emotes": "", "flags": "", "id": "0a341108-e543-45ea-a82d-c4eed38188ee", "login": "soldierghost", "mod": 0, "msg-id": "rewardgift", "msg-param-domain": "megacommerce_2019", "msg-param-selected-count": 5, "msg-param-total-reward-count": 5, "msg-param-trigger-amount": 1, "msg-param-trigger-type": "SUBSCRIPTION", "room-id": 153353959, "subscriber": 1, "system-msg": "soldierghost\'s\\\\sSub\\\\sshared\\\\srewards\\\\sto\\\\s5\\\\sothers\\\\sin\\\\sChat!", "tmi-sent-ts": 1575705003879, "user-id": 445649216, "user-type": ""}
        self.msg_param_domain = None  # ex: "msg-param-domain": "megacommerce_2019"
        self.msg_param_selected_count = None  # ex: "msg-param-selected-count": 5
        self.msg_param_total_reward_count = None  # ex: "msg-param-total-reward-count": 5
        self.msg_param_trigger_type = None  # ex: msg-param-trigger-type": "SUBSCRIPTION"
        self.msg_param_trigger_amount = None  # ex: "msg-param-trigger-amount": 1
        self.badge_info = None  # ex: subscriber/2
        self.msg_param_ritual_name = None  # ex: new-chatter
        self.msg_param_login = None  # Used in raid messages, looks same as "login" param
        self.msg_param_displayName = None  # Used in raid messages, looks same as "display-name" param
        self.msg_param_sender_name = None  # Used when user continues sub when he received subgift. This is gifter name
        self.msg_param_prior_gifter_user_name = None  # Used in "paying forward" sub after receiving gift
        self.msg_param_prior_gifter_id = None  # Used in "paying forward" sub after receiving gift
        self.msg_param_prior_gifter_display_name = None  # Used in "paying forward" sub after receiving gift
        self.msg_param_prior_gifter_anonymous = None  # Used in "paying forward" sub after receiving gift
        self.msg_param_fun_string = None  # spotted when subgift from anonymous
        self.msg_param_gift_months = None
        self.msg_param_threshold = None
        self.msg_param_was_gifted = None
        self.msg_param_multimonth_tenure = None
        self.msg_param_multimonth_duration = None
        # {"badge-info": "subscriber/10", "badges": "vip/1,subscriber/3009,twitchconAmsterdam2020/1", "color": "#FF0000", "display-name": "GetCorgi", "emotes": "", "flags": "", "id": "3ea00ae8-089a-4b81-a1ab-95435824d28f", "login": "getcorgi", "mod": 0, "msg-id": "submysterygift", "msg-param-goal-contribution-type": "SUB_POINTS", "msg-param-goal-current-contributions": 10722, "msg-param-goal-target-contributions": 10500, "msg-param-goal-user-contributions": 10, "msg-param-mass-gift-count": 10, "msg-param-origin-id": "22\\\\s1d\\\\sc3\\\\s59\\\\s99\\\\sb1\\\\s94\\\\sb0\\\\se8\\\\sa3\\\\sa3\\\\s2a\\\\s7d\\\\s26\\\\s40\\\\s5f\\\\s98\\\\s93\\\\s69\\\\s89", "msg-param-sender-count": 721, "msg-param-sub-plan": 1000, "room-id": 34711476, "subscriber": 1, "system-msg": "GetCorgi\\\\sis\\\\sgifting\\\\s10\\\\sTier\\\\s1\\\\sSubs\\\\sto\\\\sJesusAVGN\'s\\\\scommunity!\\\\sThey\'ve\\\\sgifted\\\\sa\\\\stotal\\\\sof\\\\s721\\\\sin\\\\sthe\\\\schannel!", "tmi-sent-ts": 1630605448244, "user-id": 190203376, "user-type": ""}
        self.msg_param_goal_user_contributions = None
        self.msg_param_goal_target_contributions = None
        self.msg_param_goal_current_contributions = None
        self.msg_param_goal_contribution_type = None
        self.msg_param_gift_theme = None
        self.msg_param_goal_description = None
        # {"badge-info": "subscriber/8", "badges": "subscriber/6", "color": "#9ACD32", "display-name": "Dark__Jedi", "emotes": "", "flags": "", "id": "db591379-48d8-45f9-a7b6-1023ec049b78", "login": "dark__jedi", "mod": 0, "msg-id": "resub", "msg-param-anon-gift": "false", "msg-param-cumulative-months": 8, "msg-param-gift-month-being-redeemed": 2, "msg-param-gift-months": 3, "msg-param-gifter-id": 124382767, "msg-param-gifter-login": "smash_up_", "msg-param-gifter-name": "smash_up_", "msg-param-goal-contribution-type": "SUB_POINTS", "msg-param-goal-current-contributions": 253, "msg-param-goal-target-contributions": 333, "msg-param-goal-user-contributions": 0, "msg-param-months": 0, "msg-param-should-share-streak": 1, "msg-param-streak-months": 3, "msg-param-sub-plan-name": "\\u0412\\u044b\\\\s\\u041f\\u0440\\u0435\\u043a\\u0440\\u0430\\u0441\\u043d\\u044b!", "msg-param-sub-plan": 1000, "msg-param-was-gifted": "true", "room-id": 92267843, "subscriber": 1, "system-msg": "Dark__Jedi\\\\ssubscribed\\\\sat\\\\sTier\\\\s1.\\\\sThey\'ve\\\\ssubscribed\\\\sfor\\\\s8\\\\smonths,\\\\scurrently\\\\son\\\\sa\\\\s3\\\\smonth\\\\sstreak!", "tmi-sent-ts": 1631281251127, "user-id": 488908398, "user-type": ""}
        self.msg_param_gifter_name = None
        self.msg_param_gifter_login = None
        self.msg_param_gifter_id = None
        self.msg_param_gift_month_being_redeemed = None
        self.msg_param_anon_gift = None
        # "msg-param-color": "PRIMARY"
        self.msg_param_color = None


        self.bits = None
        self.room_id = None
        self.subscriber = None
        self.system_msg = None
        self.tmi_sent_ts = None
        self.turbo = None
        self.user_id = None
        self.user_type = None
        self.known_tags = ['badges',
                           'display-name',
                           'color', 'flags',
                           'emotes',
                           'id',
                           'login',
                           'mod',
                           'msg-id',
                           'msg-param-mass-gift-count',
                           'msg-param-sender-count',
                           'msg-param-sub-plan',
                           'msg-param-sub-plan-name',
                           'msg-param-cumulative-months',
                           'msg-param-months',
                           'msg-param-should-share-streak',
                           'msg-param-origin-id',
                           'msg-param-recipient-display-name',
                           'msg-param-recipient-id',
                           'msg-param-recipient-user-name',
                           'msg-param-promo-name',
                           'msg-param-promo-gift-total',
                           'msg-param-viewerCount',
                           'msg-param-streak-months',
                           'msg-param-sender-login',
                           'msg-param-profileImageURL',
                           'msg-param-ritual-name',
                           'msg-param-trigger-type',
                           'msg-param-trigger-amount',
                           'msg-param-total-reward-count',
                           'msg-param-selected-count',
                           'msg-param-domain',
                           'msg-param-login',
                           'msg-param-displayName',
                           'msg-param-sender-name',
                           'msg-param-prior-gifter-user-name',
                           'msg-param-prior-gifter-id',
                           'msg-param-prior-gifter-display-name',
                           'msg-param-prior-gifter-anonymous',
                           'msg-param-fun-string',
                           'msg-param-gift-months',
                           'msg-param-threshold',
                           'msg-param-was-gifted',
                           'msg-param-multimonth-tenure',
                           'msg-param-multimonth-duration',
                           'msg-param-goal-user-contributions',
                           'msg-param-goal-target-contributions',
                           'msg-param-goal-current-contributions',
                           'msg-param-goal-contribution-type',
                           'msg-param-goal-description',
                           'msg-param-gift-theme',
                           'msg-param-gifter-name',
                           'msg-param-gifter-login',
                           'msg-param-gifter-id',
                           'msg-param-gift-month-being-redeemed',
                           'msg-param-anon-gift',
                           'msg-param-color',
                           'badge-info',
                           'bits',
                           'room-id',
                           'subscriber',
                           'system-msg',
                           'tmi-sent-ts',
                           'turbo',
                           'user-id',
                           'user-type'
                           ]

    async def map(self):
        self.badges = await self.get_value('badges')
        self.display_name = await self.get_value('display-name')
        self.color = await self.get_value('color')
        self.flags = await self.get_value('flags')
        self.emotes = await self.get_value('emotes')
        self.id = await self.get_value('id')
        self.login = await self.get_value('login')
        self.mod = await self.get_value('mod')

        self.msg_id = await self.get_value('msg-id')
        self.msg_param_mass_gift_count = await self.get_value('msg-param-mass-gift-count')
        self.msg_param_sender_count = await self.get_value('msg-param-sender-count')
        self.msg_param_sub_plan = await self.get_value('msg-param-sub-plan')
        self.msg_param_sub_plan_name = await self.get_value('msg-param-sub-plan-name')
        self.msg_param_cumulative_months = await self.get_value('msg-param-cumulative-months')
        self.msg_param_months = await self.get_value('msg-param-months')
        self.msg_param_should_share_streak = await self.get_value('msg-param-should-share-streak')
        self.msg_param_origin_id = await self.get_value('msg-param-origin-id')
        self.msg_param_recipient_display_name = await self.get_value('msg-param-recipient-display-name')
        self.msg_param_recipient_id = await self.get_value('msg-param-recipient-id')
        self.msg_param_recipient_user_name = await self.get_value('msg-param-recipient-user-name')
        self.msg_param_promo_name = await self.get_value('msg-param-promo-name')
        self.msg_param_promo_gift_total = await self.get_value('msg-param-promo-gift-total')
        self.msg_param_viewer_count = await self.get_value('msg-param-viewerCount')
        self.msg_param_streak_months = await self.get_value('msg-param-streak-months')
        self.msg_param_sender_login = await self.get_value('msg-param-sender-login')
        self.msg_param_sender_name = await self.get_value('msg-param-sender-name')
        self.msg_param_profile_image_url = await self.get_value('msg-param-profileImageURL')
        self.msg_param_ritual_name = await self.get_value('msg-param-ritual-name')
        self.msg_param_trigger_type = await self.get_value('msg-param-trigger-type')
        self.msg_param_trigger_amount = await self.get_value('msg-param-trigger-amount')
        self.msg_param_total_reward_count = await self.get_value('msg-param-total-reward-count')
        self.msg_param_selected_count = await self.get_value('msg-param-selected-count')
        self.msg_param_domain = await self.get_value('msg-param-domain')
        self.msg_param_login = await self.get_value('msg-param-login')
        self.msg_param_displayName = await self.get_value('msg-param-displayName')
        self.msg_param_sender_name = await self.get_value('msg-param-sender-name')
        self.msg_param_prior_gifter_user_name = await self.get_value('msg-param-prior-gifter-user-name')
        self.msg_param_prior_gifter_id = await self.get_value('msg-param-prior-gifter-id')
        self.msg_param_prior_gifter_display_name = await self.get_value('msg-param-prior-gifter-display-name')
        self.msg_param_prior_gifter_anonymous = await self.get_value('msg-param-prior-gifter-anonymous')
        self.msg_param_fun_string = await self.get_value('msg-param-fun-string')
        self.msg_param_gift_months = await self.get_value('msg-param-gift-months')
        self.msg_param_threshold = await self.get_value('msg-param-threshold')
        self.msg_param_was_gifted = await self.get_value('msg-param-was-gifted')
        self.msg_param_multimonth_tenure = await self.get_value('msg-param-multimonth-tenure')
        self.msg_param_multimonth_duration = await self.get_value('msg-param-multimonth-duration')
        self.msg_param_goal_user_contributions = await self.get_value('msg-param-goal-user-contributions')
        self.msg_param_goal_target_contributions = await self.get_value('msg-param-goal-target-contributions')
        self.msg_param_goal_current_contributions = await self.get_value('msg-param-goal-current-contributions')
        self.msg_param_goal_contribution_type = await self.get_value('msg-param-goal-contribution-type')
        self.msg_param_goal_description = await self.get_value('msg-param-goal-description')
        self.msg_param_gift_theme = await self.get_value('msg-param-gift-theme')
        self.msg_param_gifter_name = await self.get_value('msg-param-gifter-name')
        self.msg_param_gifter_login = await self.get_value('mmsg-param-gifter-login')
        self.msg_param_gifter_id = await self.get_value('msg-param-gifter-id')
        self.msg_param_gift_month_being_redeemed = await self.get_value('msg-param-gift-month-being-redeemed')
        self.msg_param_anon_gift = await self.get_value('msg-param-anon-gift')
        self.msg_param_color = await self.get_value('msg-param-color')

        self.bits = await self.get_value('bits')
        self.room_id = await self.get_value('room-id')
        self.subscriber = await self.get_value('subscriber')
        self.system_msg = await self.get_value('system-msg')
        self.tmi_sent_ts = await self.get_value('tmi-sent-ts')
        self.turbo = await self.get_value('turbo')
        self.user_id = await self.get_value('user-id')
        self.user_type = await self.get_value('user-type')
        self.badge_info = await self.get_value('badge-info')

        if self.msg_id in 'anongiftpaidupgrade,giftpaidupgrade':
            self.msg_param_sub_plan = ''

        return

    async def detect_unknown_tag(self):
        new_tags = ''

        for key in self.raw_tags.keys():
            if key not in self.known_tags:
                new_tags = ' {}{}'.format(key, new_tags)

        return new_tags

    async def get_value(self, key):
        try:
            return self.raw_tags[key]
        except Exception as e:
            return None

    async def get_gift_receiver(self):
        if self.msg_param_recipient_display_name is not None:
            return self.msg_param_recipient_display_name

        if self.msg_param_recipient_user_name is not None:
            return self.msg_param_recipient_user_name

        return ''

    async def get_user_name(self):
        if self.display_name is not None:
            return self.display_name

        if self.login is not None:
            return self.login

        if self.msg_param_sender_name is not None:
            return self.msg_param_sender_name

        if self.msg_param_sender_login is not None:
            return self.msg_param_sender_login

        return ''

    async def get_notice_count(self):
        if self.msg_param_viewer_count is not None:
            return str(self.msg_param_viewer_count)

        if self.msg_param_mass_gift_count is not None:
            return str(self.msg_param_mass_gift_count)

        if self.msg_param_cumulative_months is not None:
            return str(self.msg_param_cumulative_months)

        if self.msg_param_months is not None:
            return str(self.msg_param_months)

        return ''

    async def get_notice_count2(self):
        if self.msg_param_promo_gift_total is not None:
            return str(self.msg_param_promo_gift_total)

        if self.msg_param_sender_count is not None:
            return str(self.msg_param_sender_count)

        if self.msg_param_streak_months is not None:
            return str(self.msg_param_streak_months)

        return ''

    async def get_notice_count_int(self):
        try:
            return int(await self.get_notice_count())
        except:
            return 0

    async def get_notice_count_int2(self):
        try:
            return int(await self.get_notice_count2())
        except:
            return 0

    async def get_goal_current(self):
        try:
            return int(self.msg_param_goal_current_contributions)
        except:
            return 0

    async def get_goal_target(self):
        try:
            return int(self.msg_param_goal_target_contributions)
        except:
            return 0

    async def get_goal_added(self):
        try:
            return int(self.msg_param_goal_user_contributions)
        except:
            return 0

    async def get_goal_remaining(self):
        return (await self.get_goal_target()) - (await self.get_goal_current())

    # Returns true if subscribe message was generated by massgift message
    def is_submessage_from_massgift(self):
        return self.msg_param_origin_id is not None and self.msg_param_mass_gift_count is None

    def is_announcement(self):
        return self.msg_id == 'announcement'

    # Disable messaging of mass-gifting, avoid crashes
    # Skip announcements
    def can_react(self):
        return not self.is_submessage_from_massgift() and not self.is_announcement()
