import logging, os
import logging.config

app_name = os.getenv('KB_APP')
if app_name is None:
    app_name = ''
if app_name != '':
    app_name += '.'

log_dir = os.getenv('KB_LOG_DIR')
if log_dir is None:
    log_dir = 'log/'

if not log_dir.endswith('/'):
    log_dir += '/'

GLOBAL_LOG_LEVEL = "INFO"
GLOBAL_ENCODING = "utf-8"

LOG_TWITCH_PATH = log_dir + app_name + 'twitch.log'
LOG_API_PATH = log_dir + app_name + 'api.log'
LOG_DB_PATH = log_dir + app_name + 'db.log'
LOG_TG_AUTH_PATH = log_dir + app_name + 'auth.log'
LOG_TG_INFO_PATH = log_dir + app_name + 'infobot.log'
LOG_INFO_MANAGER_PATH = log_dir + app_name + 'infomanager.log'
LOG_TG_PATH = log_dir + app_name + 'tg.log'
LOG_SANIC_PATH = log_dir + app_name + 'sanic.log'
LOG_TIO_PATH = log_dir + app_name + 'twitchio.log'
LOG_SPAM_DETECTOR_PATH = log_dir + app_name + 'spamdetector.log'
LOG_IRC = log_dir + app_name + 'irc.log'
GLOBAL_PRAPOGATE = False

KRYA_LOGGING_CONFIG = dict(
    version=1,
    disable_existing_loggers=False,
    loggers={
        "sanic.root": {
            "level": GLOBAL_LOG_LEVEL,
            "handlers": ["file.sanic.error"]
        },
        "sanic.error": {
            "level": GLOBAL_LOG_LEVEL,
            "handlers": ["file.sanic.error"],
            "propagate": GLOBAL_PRAPOGATE,
            "qualname": "sanic.error",
        },
        "sanic.access": {
            "level": GLOBAL_LOG_LEVEL,
            "handlers": ["file.sanic.access"],
            "propagate": GLOBAL_PRAPOGATE,
            "qualname": "sanic.access",
        },
        "krya.sanic": {
            "level": GLOBAL_LOG_LEVEL,
            "handlers": ["file.sanic.default"],
            "propagate": GLOBAL_PRAPOGATE,
            "qualname": "krya.sanic",
        },
        "krya.twitch": {
            "level": GLOBAL_LOG_LEVEL,
            "handlers": ["file.twitch"],
            "propagate": GLOBAL_PRAPOGATE,
            "qualname": "krya.twitch",
        },
        "krya.tg": {
            "level": GLOBAL_LOG_LEVEL,
            "handlers": ["file.tg"],
            "propagate": GLOBAL_PRAPOGATE,
            "qualname": "krya.tg",
        },
        "krya.api": {
            "level": GLOBAL_LOG_LEVEL,
            "handlers": ["file.api"],
            "propagate": GLOBAL_PRAPOGATE,
            "qualname": "krya.api",
        },
        "krya.db": {
            "level": GLOBAL_LOG_LEVEL,
            "handlers": ["file.db"],
            "propagate": GLOBAL_PRAPOGATE,
            "qualname": "krya.db",
        },
        "aiomysql": {
            "level": GLOBAL_LOG_LEVEL,
            "handlers": ["file.db"],
            "propagate": GLOBAL_PRAPOGATE,
            "qualname": "aiomysql",
        },
        "krya.auth": {
            "level": GLOBAL_LOG_LEVEL,
            "handlers": ["file.auth"],
            "propagate": GLOBAL_PRAPOGATE,
            "qualname": "krya.auth",
        },
        "krya.infobot": {
            "level": GLOBAL_LOG_LEVEL,
            "handlers": ["file.infobot"],
            "propagate": GLOBAL_PRAPOGATE,
            "qualname": "krya.infobot",
        },
        "krya.infomanager": {
            "level": GLOBAL_LOG_LEVEL,
            "handlers": ["file.infomanager"],
            "propagate": GLOBAL_PRAPOGATE,
            "qualname": "krya.infomanager",
        },
        "streamlink": {
            "level": GLOBAL_LOG_LEVEL,
            "handlers": ["file.infomanager"],
            "propagate": GLOBAL_PRAPOGATE,
            "qualname": "streamlink",
        },
        "krya.spam": {
            "level": GLOBAL_LOG_LEVEL,
            "handlers": ["file.spam"],
            "propagate": GLOBAL_PRAPOGATE,
            "qualname": "krya.spam",
        },
        "krya.irc": {
            "level": GLOBAL_LOG_LEVEL,
            "handlers": ["file.irc"],
            "propagate": GLOBAL_PRAPOGATE,
            "qualname": "krya.irc",
        },
        "twitchio.websocket": {
            "level": GLOBAL_LOG_LEVEL,
            "handlers": ["file.twitchio"],
            "propagate": GLOBAL_PRAPOGATE,
            "qualname": "twitchio.websocket",
        },
        "twitchio": {
            "level": GLOBAL_LOG_LEVEL,
            "handlers": ["file.twitchio"],
            "propagate": GLOBAL_PRAPOGATE,
            "qualname": "twitchio",
        },
        "twitchio.http": {
            "level": GLOBAL_LOG_LEVEL,
            "handlers": ["file.twitchio"],
            "propagate": GLOBAL_PRAPOGATE,
            "qualname": "twitchio.http",
        },
        "websockets.server": {
            "level": GLOBAL_LOG_LEVEL,
            "handlers": ["file.twitchio"],
            "propagate": GLOBAL_PRAPOGATE,
            "qualname": "websockets.server",
        },
        "websockets.protocol": {
            "level": GLOBAL_LOG_LEVEL,
            "handlers": ["file.twitchio"],
            "propagate": GLOBAL_PRAPOGATE,
            "qualname": "websockets.server",
        },
        "schedule": {
            "level": GLOBAL_LOG_LEVEL,
            "handlers": ["file.tg"],
            "propagate": GLOBAL_PRAPOGATE,
            "qualname": "schedule",
        }
    },
    handlers={
        'file.sanic.error': {
            'class': 'logging.FileHandler',
            'filename': LOG_SANIC_PATH,
            'formatter': 'sanic.generic',
            'encoding': GLOBAL_ENCODING,
        },
        'file.sanic.access': {
            'class': 'logging.FileHandler',
            'filename': LOG_SANIC_PATH,
            'formatter': 'sanic.access',
            'encoding': GLOBAL_ENCODING,
        },
        'file.sanic.default': {
            'class': 'logging.FileHandler',
            'filename': LOG_SANIC_PATH,
            'formatter': 'default',
            'encoding': GLOBAL_ENCODING,
        },
        'file.twitch': {
            'class': 'logging.FileHandler',
            'filename': LOG_TWITCH_PATH,
            'formatter': 'default',
            'encoding': GLOBAL_ENCODING,
        },
        'file.api': {
            'class': 'logging.FileHandler',
            'filename': LOG_API_PATH,
            'formatter': 'default',
            'encoding': GLOBAL_ENCODING,
        },
        'file.tg': {
            'class': 'logging.FileHandler',
            'filename': LOG_TG_PATH,
            'formatter': 'default',
            'encoding': GLOBAL_ENCODING,
        },
        'file.db': {
            'class': 'logging.FileHandler',
            'filename': LOG_DB_PATH,
            'formatter': 'default',
            'encoding': GLOBAL_ENCODING,
        },
        'file.auth': {
            'class': 'logging.FileHandler',
            'filename': LOG_TG_AUTH_PATH,
            'formatter': 'default',
            'encoding': GLOBAL_ENCODING,
        },
        'file.infobot': {
            'class': 'logging.FileHandler',
            'filename': LOG_TG_INFO_PATH,
            'formatter': 'default',
            'encoding': GLOBAL_ENCODING,
        },
        'file.infomanager': {
            'class': 'logging.FileHandler',
            'filename': LOG_INFO_MANAGER_PATH,
            'formatter': 'default',
            'encoding': GLOBAL_ENCODING,
        },
        'file.twitchio': {
            'class': 'logging.FileHandler',
            'filename': LOG_TIO_PATH,
            'formatter': 'default',
            'encoding': GLOBAL_ENCODING,
        },
        'file.spam': {
            'class': 'logging.FileHandler',
            'filename': LOG_SPAM_DETECTOR_PATH,
            'formatter': 'default',
            'encoding': GLOBAL_ENCODING,
        },
        'file.irc': {
            'class': 'logging.FileHandler',
            'filename': LOG_IRC,
            'formatter': 'default',
            'encoding': GLOBAL_ENCODING,
        },
    },
    formatters={
        "default": {
            "format": "%(asctime)s [ %(levelname)s ] [%(filename)s:%(lineno)s - %(funcName)20s() ] %(message)s",
            "datefmt": "[%Y-%m-%d %H:%M:%S %z]",
            "class": "logging.Formatter"
        },
        "sanic.generic": {
            "format": "%(asctime)s [%(levelname)s] [%(process)d] %(message)s",
            "datefmt": "[%Y-%m-%d %H:%M:%S %z]",
            "class": "logging.Formatter",
        },
        "sanic.access": {
            "format": "%(asctime)s[%(levelname)s][(%(name)s)][%(host)s]: "
            + "%(request)s %(message)s %(status)d %(byte)d",
            "datefmt": "[%Y-%m-%d %H:%M:%S %z]",
            "class": "logging.Formatter",
        },
    },
)


def load_config():
    logging.config.dictConfig(KRYA_LOGGING_CONFIG)