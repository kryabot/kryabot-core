import logging, os
import logging.config

log_dir = os.getenv('LOG_DIR')
if log_dir is None:
    log_dir = 'log/'

GLOBAL_LOG_LEVEL = "INFO"
GLOBAL_ENCODING = "utf-8"

LOG_TWITCH_PATH = log_dir + 'twitch.log'
LOG_API_PATH = log_dir + 'api.log'
LOG_DB_PATH = log_dir + 'db.log'
LOG_TG_AUTH_PATH = log_dir + 'auth.log'
LOG_TG_INFO_PATH = log_dir + 'infobot.log'
LOG_INFO_MANAGER_PATH = log_dir + 'infomanager.log'
LOG_TG_PATH = log_dir + 'tg.log'
LOG_SANIC_PATH = log_dir + 'sanic.log'
LOG_TIO_PATH = log_dir + 'twitchio.log'

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
            "propagate": True,
            "qualname": "sanic.error",
        },
        "sanic.access": {
            "level": GLOBAL_LOG_LEVEL,
            "handlers": ["file.sanic.access"],
            "propagate": True,
            "qualname": "sanic.access",
        },
        "krya.sanic": {
            "level": GLOBAL_LOG_LEVEL,
            "handlers": ["file.sanic.default"],
            "propagate": True,
            "qualname": "krya.sanic",
        },
        "krya.twitch": {
            "level": GLOBAL_LOG_LEVEL,
            "handlers": ["file.twitch"],
            "propagate": True,
            "qualname": "krya.twitch",
        },
        "krya.tg": {
            "level": GLOBAL_LOG_LEVEL,
            "handlers": ["file.tg"],
            "propagate": True,
            "qualname": "krya.tg",
        },
        "krya.api": {
            "level": GLOBAL_LOG_LEVEL,
            "handlers": ["file.api"],
            "propagate": True,
            "qualname": "krya.api",
        },
        "krya.db": {
            "level": GLOBAL_LOG_LEVEL,
            "handlers": ["file.db"],
            "propagate": True,
            "qualname": "krya.db",
        },
        "aiomysql": {
            "level": GLOBAL_LOG_LEVEL,
            "handlers": ["file.db"],
            "propagate": True,
            "qualname": "aiomysql",
        },
        "krya.auth": {
            "level": GLOBAL_LOG_LEVEL,
            "handlers": ["file.auth"],
            "propagate": True,
            "qualname": "krya.auth",
        },
        "krya.infobot": {
            "level": GLOBAL_LOG_LEVEL,
            "handlers": ["file.infobot"],
            "propagate": True,
            "qualname": "krya.infobot",
        },
        "krya.infomanager": {
            "level": GLOBAL_LOG_LEVEL,
            "handlers": ["file.infomanager"],
            "propagate": True,
            "qualname": "krya.infomanager",
        },
        "twitchio.websocket": {
            "level": GLOBAL_LOG_LEVEL,
            "handlers": ["file.twitchio"],
            "propagate": True,
            "qualname": "twitchio.websocket",
        },
        "twitchio": {
            "level": GLOBAL_LOG_LEVEL,
            "handlers": ["file.twitchio"],
            "propagate": True,
            "qualname": "twitchio",
        },
        "twitchio.http": {
            "level": GLOBAL_LOG_LEVEL,
            "handlers": ["file.twitchio"],
            "propagate": True,
            "qualname": "twitchio.http",
        },
        "websockets.server": {
            "level": GLOBAL_LOG_LEVEL,
            "handlers": ["file.twitchio"],
            "propagate": True,
            "qualname": "websockets.server",
        },
        "websockets.protocol": {
            "level": GLOBAL_LOG_LEVEL,
            "handlers": ["file.twitchio"],
            "propagate": True,
            "qualname": "websockets.server",
        },
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