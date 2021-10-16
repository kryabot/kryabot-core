import logging, os
import logging.config
import ecs_logging

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


class CustomStdlibFormatter(ecs_logging.StdlibFormatter):
    def format_to_ecs(self, record):
        result = super().format_to_ecs(record)
        # Append app field to recognise application
        result["app"] = os.getenv('KB_APP', 'unknown')
        del result["process"]
        del result["log"]["original"]
        return result


JSON_OUTPUT_FILE = log_dir + app_name + 'json.log'
DEFAULT_JSON_HANDLER_NAME = 'file.json'
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
LOG_SPAM_DETECTOR_PATH = log_dir + 'spamdetector.log'
LOG_IRC = log_dir + 'irc.log'
GLOBAL_PRAPOGATE = False
GLOBAL_FILE_CLASS = 'logging.handlers.WatchedFileHandler'

KRYA_LOGGING_CONFIG = dict(
    version=1,
    disable_existing_loggers=False,
    loggers={
        "sanic.root": {
            "level": GLOBAL_LOG_LEVEL,
            "handlers": [DEFAULT_JSON_HANDLER_NAME]
        },
        "sanic.error": {
            "level": GLOBAL_LOG_LEVEL,
            "handlers": [DEFAULT_JSON_HANDLER_NAME],
            "propagate": GLOBAL_PRAPOGATE,
            "qualname": "sanic.error",
        },
        "sanic.access": {
            "level": GLOBAL_LOG_LEVEL,
            "handlers": [DEFAULT_JSON_HANDLER_NAME],
            "propagate": GLOBAL_PRAPOGATE,
            "qualname": "sanic.access",
        },
        "krya.sanic": {
            "level": GLOBAL_LOG_LEVEL,
            "handlers": [DEFAULT_JSON_HANDLER_NAME],
            "propagate": GLOBAL_PRAPOGATE,
            "qualname": "krya.sanic",
        },
        "krya.twitch": {
            "level": GLOBAL_LOG_LEVEL,
            "handlers": [DEFAULT_JSON_HANDLER_NAME],
            "propagate": GLOBAL_PRAPOGATE,
            "qualname": "krya.twitch",
        },
        "krya.tg": {
            "level": GLOBAL_LOG_LEVEL,
            "handlers": [DEFAULT_JSON_HANDLER_NAME],
            "propagate": GLOBAL_PRAPOGATE,
            "qualname": "krya.tg",
        },
        "krya.api": {
            "level": GLOBAL_LOG_LEVEL,
            "handlers": [DEFAULT_JSON_HANDLER_NAME],
            "propagate": GLOBAL_PRAPOGATE,
            "qualname": "krya.api",
        },
        "krya.db": {
            "level": GLOBAL_LOG_LEVEL,
            "handlers": [DEFAULT_JSON_HANDLER_NAME],
            "propagate": GLOBAL_PRAPOGATE,
            "qualname": "krya.db",
        },
        "aiomysql": {
            "level": GLOBAL_LOG_LEVEL,
            "handlers": [DEFAULT_JSON_HANDLER_NAME],
            "propagate": GLOBAL_PRAPOGATE,
            "qualname": "aiomysql",
        },
        "krya.auth": {
            "level": GLOBAL_LOG_LEVEL,
            "handlers": [DEFAULT_JSON_HANDLER_NAME],
            "propagate": GLOBAL_PRAPOGATE,
            "qualname": "krya.auth",
        },
        "krya.infobot": {
            "level": GLOBAL_LOG_LEVEL,
            "handlers": [DEFAULT_JSON_HANDLER_NAME],
            "propagate": GLOBAL_PRAPOGATE,
            "qualname": "krya.infobot",
        },
        "krya.infomanager": {
            "level": GLOBAL_LOG_LEVEL,
            "handlers": [DEFAULT_JSON_HANDLER_NAME],
            "propagate": GLOBAL_PRAPOGATE,
            "qualname": "krya.infomanager",
        },
        "streamlink": {
            "level": GLOBAL_LOG_LEVEL,
            "handlers": [DEFAULT_JSON_HANDLER_NAME],
            "propagate": GLOBAL_PRAPOGATE,
            "qualname": "streamlink",
        },
        "krya.spam": {
            "level": GLOBAL_LOG_LEVEL,
            "handlers": [DEFAULT_JSON_HANDLER_NAME],
            "propagate": GLOBAL_PRAPOGATE,
            "qualname": "krya.spam",
        },
        "krya.irc": {
            "level": GLOBAL_LOG_LEVEL,
            "handlers": [DEFAULT_JSON_HANDLER_NAME],
            "propagate": GLOBAL_PRAPOGATE,
            "qualname": "krya.irc",
        },
        "twitchio.websocket": {
            "level": GLOBAL_LOG_LEVEL,
            "handlers": [DEFAULT_JSON_HANDLER_NAME],
            "propagate": GLOBAL_PRAPOGATE,
            "qualname": "twitchio.websocket",
        },
        "twitchio": {
            "level": GLOBAL_LOG_LEVEL,
            "handlers": [DEFAULT_JSON_HANDLER_NAME],
            "propagate": GLOBAL_PRAPOGATE,
            "qualname": "twitchio",
        },
        "twitchio.http": {
            "level": GLOBAL_LOG_LEVEL,
            "handlers": [DEFAULT_JSON_HANDLER_NAME],
            "propagate": GLOBAL_PRAPOGATE,
            "qualname": "twitchio.http",
        },
        "websockets.server": {
            "level": GLOBAL_LOG_LEVEL,
            "handlers": [DEFAULT_JSON_HANDLER_NAME],
            "propagate": GLOBAL_PRAPOGATE,
            "qualname": "websockets.server",
        },
        "websockets.protocol": {
            "level": GLOBAL_LOG_LEVEL,
            "handlers": [DEFAULT_JSON_HANDLER_NAME],
            "propagate": GLOBAL_PRAPOGATE,
            "qualname": "websockets.server",
        },
        "schedule": {
            "level": GLOBAL_LOG_LEVEL,
            "handlers": [DEFAULT_JSON_HANDLER_NAME],
            "propagate": GLOBAL_PRAPOGATE,
            "qualname": "schedule",
        }
    },
    handlers={
        DEFAULT_JSON_HANDLER_NAME : {
            'class': GLOBAL_FILE_CLASS,
            'filename': JSON_OUTPUT_FILE,
            'formatter': 'json_formatter',
            'encoding': GLOBAL_ENCODING
        },
        'file.sanic.error': {
            'class': GLOBAL_FILE_CLASS,
            'filename': LOG_SANIC_PATH,
            'formatter': 'sanic.generic',
            'encoding': GLOBAL_ENCODING,
        },
        'file.sanic.access': {
            'class': GLOBAL_FILE_CLASS,
            'filename': LOG_SANIC_PATH,
            'formatter': 'sanic.access',
            'encoding': GLOBAL_ENCODING,
        },
        'file.sanic.default': {
            'class': GLOBAL_FILE_CLASS,
            'filename': LOG_SANIC_PATH,
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
        "json_formatter": {
            'class': 'utils.json_log.CustomStdlibFormatter'
        }
    },
)


def load_config():
    logging.config.dictConfig(KRYA_LOGGING_CONFIG)