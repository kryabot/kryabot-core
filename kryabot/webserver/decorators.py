import functools
import logging
from webserver.common import get_param_value
from sanic.response import json

IP_WHITELIST = []
IP_WHITELIST.append('213.226.189.248')  # API server
IP_WHITELIST.append('86.38.4.77')  # support
IP_WHITELIST.append('172.18.0.1')
#IP_WHITELIST.append('127.0.0.1')  # DEV

TOKEN_WHITELIST = []
TOKEN_WHITELIST.append('token')


def user(mandatory=True):
    def decorator(f):
        @functools.wraps(f)
        async def decorated_function(self, request, *args, **kwargs):
            user_id = find_user_id(request)
            if not mandatory or user_id > 0:
                return await f(self, request, user_id, *args, **kwargs)
            else:
                return json({'code': 0, 'message': 'no_input'}, status=200)
        return decorated_function
    return decorator


def authorized():
    def decorator(f):
        @functools.wraps(f)
        async def decorated_function(self, request, *args, **kwargs):
            if is_authorized(request, IP_WHITELIST, TOKEN_WHITELIST):
                return await f(self, request, *args, **kwargs)
            else:
                # the user is not authorized.
                return json({'code': 0, 'message': 'not_authorized'}, status=403)
        return decorated_function
    return decorator


def authorized_token(request, token_whitelist) -> bool:
    return get_param_value(request, 'token') in token_whitelist


def authorized_ip(request, ip_whitelist) -> bool:
    auth = request.ip in ip_whitelist
    if not auth:
        logger = logging.getLogger('krya.tg')
        logger.warning('Unauthorized IP {0} tried to access {1}'.format(request.ip, request.url))

    return auth


def is_authorized(request, ip_whitelist, token_whitelist) -> bool:
    return authorized_ip(request, ip_whitelist)
    #return authorized_token(request, token_whitelist) and authorized_ip(request, ip_whitelist)


def find_user_id(request)->int:
    possible_keys = ['user_id', 'userId']

    user_id = None
    for key in possible_keys:
        user_id = get_param_value(request, key)
        if user_id is not None:
            break

    try:
        return int(user_id)
    except:
        return 0

