import asyncio
import logging

from sanic import Sanic
from sanic.request import Request
from sanic.response import text, json
from sanic.exceptions import NotFound, ServerError
from object.BotConfig import BotConfig
from tgbot.KryaClient import KryaClient
from webserver.common import get_value, get_param_value
from webserver.decorators import authorized, user
import utils.redis_key as redis_key


class WebHandler:
    def __init__(self, loop, cfg):
        self.redis = None
        self.logger: logging.Logger = logging.getLogger('krya.sanic')
        self.cfg: BotConfig = cfg
        self.bot_token = self.cfg.getGuardBotConfig()['TOKEN']
        self.admin_token = 'g4h56984984dr98d4gd1rg98s198s4g9s8e4g'
        self.app: Sanic = Sanic("krya.sanic", configure_logging=False)
        self.server = None
        self.loop = loop
        self.guard_bot: KryaClient = None

    def register_routes(self):
        self.logger.info('Registering sanic routes')

        # Routes
        self.app.add_route(self.hello_world, '/', methods=['GET'])
        self.app.add_route(self.endpoint_tg_refresh_members, '/tg/refresh-group-members', methods=['GET'])
        self.app.add_route(self.endpoint_tg_join_group, '/tg/join_group', methods=['GET'])
        self.app.add_route(self.endpoint_tg_update, '/tg/update', methods=['GET'])
        self.app.add_route(self.endpoint_tg_update_special_rights, '/tg/update_special_rights', methods=['GET'])
        self.app.add_route(self.endpoint_tg_mass_kick, '/tg/mass_kick', methods=['POST'])
        self.app.add_route(self.endpoint_tg_report_error, '/tg/error_report', methods=['POST'])
        self.app.add_route(self.endpoint_tg_point_action_mute, '/tg/actions/mute', methods=['POST'])
        self.app.add_route(self.endpoint_tg_point_action_message, '/tg/actions/message', methods=['POST'])

        self.app.add_route(self.endpoint_twitch_unsubscribe_event, '/twitch/report_unsub', methods=['GET'])
        self.app.add_route(self.endpoint_twitch_unlink, '/twitch/tg_unlink', methods=['POST'])
        self.app.add_route(self.endpoint_twitch_stream_update, 'twitch/stream_update', methods=['POST'])

        self.app.add_route(self.endpoint_sync, '/sync', methods=['GET'])

        # Error handlers
        self.app.error_handler.add(ServerError, self.handle_error)
        self.app.error_handler.add(NotFound, self.handle_not_found)

    async def start(self, guard_bot: KryaClient):
    #async def start(self):
        self.guard_bot = guard_bot
        self.register_routes()

        server = self.app.create_server(host="0.0.0.0", port=5000, return_asyncio_server=True)
        self.server = asyncio.ensure_future(server, loop=self.loop)

    async def stop(self):
        self.app.stop()

    @authorized()
    @user()
    async def hello_world(self, request: Request, user_id: int):
        return text('hellow world ' + str(user_id))

    def handle_error(self, request: Request, exception: Exception):
        self.logger.exception(exception)

        if self.guard_bot and self.guard_bot.is_connected():
            try:
                self.loop.create_task(self.guard_bot.report_exception(exception, request.url))
            except Exception as ex:
                self.logger.error('Failed to report http exception to monitoring')
                self.logger.exception(ex)

        return json({}, status=500)

    def handle_not_found(self, request, exception):
        return json({'status': 404, 'message': self.get_message('404')}, status=404)

    async def todo(self, request: Request):
        return text('todo: ' + request.url)

    def get_message(self, key):
        return {
            '404': 'Not found',
            '401': 'Not authorized',
        }.get(key, '')

    def response_success(self):
        return json({'code': 1, 'message': 'Accepted'}, status=200)

    def response_bad_input(self):
        return json({'code': 0, 'message': 'No input'}, status=200)

    @authorized()
    @user()
    async def endpoint_tg_refresh_members(self, request: Request, user_id: int):
        self.loop.create_task(self.guard_bot.run_channel_refresh_remote(user_id, False, None))
        return self.response_success()

    @authorized()
    @user()
    async def endpoint_tg_join_group(self, request: Request, user_id: int):
        self.loop.create_task(self.guard_bot.join_channel(user_id))
        return self.response_success()

    @authorized()
    async def endpoint_tg_update(self, request: Request):
        await self.guard_bot.update_data()
        return self.response_success()

    @authorized()
    async def endpoint_tg_update_special_rights(self, request: Request):
        await self.guard_bot.init_special_rights()
        return self.response_success()

    @authorized()
    @user()
    async def endpoint_tg_mass_kick(self, request: Request, user_id: int):
        body = request.json
        if body is None:
            return self.response_bad_input()

        self.loop.create_task(self.guard_bot.run_channel_refresh_remote(user_id, True, body))
        return self.response_success()

    @authorized()
    @user()
    async def endpoint_tg_report_error(self, request: Request, user_id: int):
        body = request.json
        if body is None:
            return self.response_bad_input()

        await self.guard_bot.report_to_monitoring('ERR for user id {}\n\n<pre>{}</pre>'.format(user_id, body))
        return self.response_success()

    @authorized()
    async def endpoint_tg_point_action_mute(self, request: Request):
        if request.json is None:
            return self.response_bad_input()

        from_user_id = get_value('from_user_id', request.json)
        target_user_id = get_value('target_user_id', request.json)
        channel_id = get_value('channel_id', request.json)
        duration = get_value('duration', request.json)

        try:
            result = self.guard_bot.mute_from_twitch(from_user_id, target_user_id, channel_id, duration)
        except Exception as ex:
            self.logger.exception(ex)
            result = False

        return json({'code': 1, 'message': 'Accepted', 'result': result}, 200)

    @authorized()
    @user()
    async def endpoint_tg_point_action_message(self, request: Request, user_id: int):
        if request.json is None:
            return self.response_bad_input()

        from_user_id = get_value('from_user_id', request.json)
        channel_id = get_value('channel_id', request.json)
        message = get_value('message', request.json)
        try:
            result = self.guard_bot.message_from_twitch(from_user_id, channel_id, message)
        except Exception as ex:
            self.logger.exception(ex)
            result = False

        return json({'code': 1, 'message': 'Accepted', 'result': result}, 200)

    @authorized()
    async def endpoint_twitch_unsubscribe_event(self, request: Request):
        event_id = get_param_value(request, 'event_id')
        if event_id is None:
            return self.response_bad_input()

        self.loop.create_task(self.guard_bot.twitch_event_unsubscribe(event_id))
        return self.response_success()

    @authorized()
    async def endpoint_twitch_unlink(self, request: Request):
        body = request.json
        if body is None:
            return self.response_bad_input()

        unlink_tg_id = get_value('tg_user_id', body)
        unlink_tw_id = get_value('tw_user_id', body)
        unlink_kb_id = get_value('user_id', body)

        self.loop.create_task(self.guard_bot.handle_person_unlink(unlink_tg_id, unlink_tw_id, unlink_kb_id, body))
        return self.response_success()

    @authorized()
    async def endpoint_twitch_stream_update(self, request: Request):
        await self.guard_bot.db.redis.push_list_to_right(redis_key.get_streams_data(), request.json)
        return self.response_success()

    @authorized()
    @user()
    async def endpoint_sync(self, request: Request, user_id: int):
        topic = get_param_value(request, 'topic')
        if topic is None:
            return self.response_bad_input()

        await self.guard_bot.sync_router(user_id, topic)
        return self.response_success()
