

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
