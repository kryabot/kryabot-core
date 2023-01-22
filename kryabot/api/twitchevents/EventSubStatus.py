from enum import Enum


class EventSubStatus(Enum):
    ENABLED = 'enabled'
    PENDING = 'webhook_callback_verification_pending'
    FAILED = 'webhook_callback_verification_failed'
    FAILURES = 'notification_failures_exceeded'
    AUTH_REVOKED = 'authorization_revoked'
    USER_REMOVED = 'user_removed'
