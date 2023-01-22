from enum import Enum


class EventSubType(Enum):
    CHANNEL_UPDATE = 'channel.update'
    CHANNEL_FOLLOW = 'channel.follow'
    CHANNEL_SUBSCRIBE = 'channel.subscribe', ['channel:read:subscriptions']
    CHANNEL_SUBSCRIBE_END = 'channel.subscription.end', ['channel:read:subscriptions']
    CHANNEL_SUBSCRIBE_GIFT = 'channel.subscription.gift', ['channel:read:subscriptions']
    CHANNEL_SUBSCRIBE_MESSAGE = 'channel.subscription.message', ['channel:read:subscriptions']
    CHANNEL_CHEER = 'channel.cheer', ['bits:read']
    CHANNEL_RAID = 'channel.raid'
    CHANNEL_BAN = 'channel.ban', ['channel:moderate']
    CHANNEL_UNBAN = 'channel.unban', ['channel:moderate']
    CHANNEL_MOD_ADD = 'channel.moderator.add', ['channel:moderate']
    CHANNEL_MOD_REMOVE = 'channel.moderator.remove', ['channel:moderate']
    CHANNEL_POINTS_UPDATE = 'channel.channel_points_custom_reward.update', ['channel:read:redemptions', 'channel:manage:redemptions']
    CHANNEL_POINTS_REMOVE = 'channel.channel_points_custom_reward.remove', ['channel:read:redemptions', 'channel:manage:redemptions']
    CHANNEL_POINTS_REDEMPTION_UPDATE = 'channel.channel_points_custom_reward_redemption.update', ['channel:read:redemptions', 'channel:manage:redemptions']
    CHANNEL_POINTS_REDEMPTION_NEW = 'channel.channel_points_custom_reward_redemption.add', ['channel:read:redemptions', 'channel:manage:redemptions']
    CHANNEL_POLL_BEGIN = 'channel.poll.begin', ['channel:read:polls', 'channel:manage:polls']
    CHANNEL_POLL_PROGRESS = 'channel.poll.progress', ['channel:read:polls', 'channel:manage:polls']
    CHANNEL_POLL_END = 'channel.poll.end', ['channel:read:polls', 'channel:manage:polls']
    CHANNEL_PREDICTION_BEGIN = 'channel.prediction.begin', ['channel:read:predictions', 'channel:manage:predictions']
    CHANNEL_PREDICTION_PROCESS = 'channel.prediction.progress', ['channel:read:predictions', 'channel:manage:predictions']
    CHANNEL_PREDICTION_LOCK = 'channel.prediction.lock', ['channel:read:predictions', 'channel:manage:predictions']
    CHANNEL_PREDICTION_END = 'channel.prediction.end', ['channel:read:predictions', 'channel:manage:predictions']
    CHANNEL_GOAL_BEGIN = 'channel.goal.begin', ['channel:read:goals']
    CHANNEL_GOAL_PROGRESS = 'channel.goal.progress', ['channel:read:goals']
    CHANNEL_GOAL_END = 'channel.goal.end', ['channel:read:goals']
    CHANNEL_HYPE_TRAIN_BEGIN = 'channel.hype_train.begin', ['channel:read:hype_train']
    CHANNEL_HYPE_TRAIN_PROGRESS = 'channel.hype_train.progress', ['channel:read:hype_train']
    CHANNEL_HYPE_TRAIN_END = 'channel.hype_train.end', ['channel:read:hype_train']
    STREAM_ONLINE = 'stream.online'
    STREAM_OFFLINE = 'stream.offline'
    AUTH_GRANTED = 'user.authorization.grant'
    AUTH_REVOKED = 'user.authorization.revoke'
    USER_UPDATE = 'user.update'

    def __init__(self, key, scopes=None):
        self.key = key
        self.scopes = scopes

    def __new__(cls, key, scopes=None):
        obj = object.__new__(cls)
        obj._value_ = key
        return obj

    def eq(self, expected)->bool:
        return expected == self
