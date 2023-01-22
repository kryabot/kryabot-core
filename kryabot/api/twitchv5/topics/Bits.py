from abc import ABC

from api.twitchv5.TopicInterface import TopicInterface


class Bits(TopicInterface, ABC):

    async def get_total_bits_by_user(self, broadcaster_tw_id, user_tw_id, token, period='all'):
        url = '{base}bits/leaderboard?count=1&user_id={user_id}&period={period}'.format(base=self.hostname, user_id=user_tw_id, period=period)
        headers = await self.get_json_headers(bearer_token=token)
        return await self.make_get_request(url, headers=headers)

    async def get_bits_top(self, token, period='all', count=10):
        url = '{base}bits/leaderboard?count={cnt}&period={period}'.format(base=self.hostname, cnt=count, period=period)
        headers = await self.get_json_headers(bearer_token=token)

        return await self.make_get_request(url, headers=headers)