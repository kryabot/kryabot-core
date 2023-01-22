from abc import ABC

from api.twitchv5.TopicInterface import TopicInterface
from utils.twitch import app_auth


class Games(TopicInterface, ABC):
    @app_auth()
    async def get_game_info(self, game_id):
        key = self.redis_keys.get_twitch_game_info(game_id)
        response = await self.redis.get_parsed_value_by_key(key)

        if response is None:
            headers = await self.get_json_headers()
            url = '{}games?id={}'.format(self.hostname, game_id)
            response = await self.make_get_request(url, headers=headers)
            await self.redis.set_parsed_value_by_key(key, response, self.redis_keys.ttl_month)

        return response
