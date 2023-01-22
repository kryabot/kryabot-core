from api.core import Core
from utils.json_parser import dict_to_json


class GuardBot(Core):
    def __init__(self):
        super().__init__()
        self.base_url = self.cfg.getGuardBotConfig()['HOST']
        self.token = self.cfg.getGuardBotConfig()['TOKEN']

    async def send_stream_notification(self, channel_tw_id, channel_name, action, data):
        url = "{burl}{call_method}?token={tk}".format(burl=self.base_url,call_method='/twitch/notification', tk=self.token)
        body = {
            'channel_tw_id': channel_tw_id,
            'channel_name': channel_name,
            'action': action,
            'data': data
        }

        return await self.make_post_request(url=url, body=body)

    async def notify_tg_unlink(self, user_id, tw_user_id, tg_user_id):
        url = "{burl}{call_method}?token={tk}".format(burl=self.base_url, call_method='/twitch/tg_unlink', tk=self.token)
        body = {
            'user_id': user_id,
            'tw_user_id': tw_user_id,
            'tg_user_id': tg_user_id,
        }
        return await self.make_post_request(url=url, body=body)

    async def report_problem(self, message_from, topic, message):
        url = "{burl}{call_method}?token={tk}&userId=0".format(burl=self.base_url, call_method='/tg/error_report', tk=self.token)
        body = {
            'from': message_from,
            'topic': topic,
            'data': dict_to_json(message)
        }
        return await self.make_post_request(url=url, body=body)

    async def tg_mute(self, channel_id, from_user_id, target_user_id, duration):
        url = "{burl}{call_method}?token={tk}".format(burl=self.base_url, call_method='/tg/action_mute_user', tk=self.token)
        body = {
            'from_user_id': from_user_id,
            'target_user_id': target_user_id,
            'channel_id': channel_id,
            'duration': duration
        }

        return await self.make_post_request(url=url, body=body)