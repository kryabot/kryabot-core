from typing import List

from aiohttp import ClientResponseError

from api.core import Core


class Wasd(Core):
    def __init__(self):
        super().__init__()
        self.hostname: str = "https://wasd.tv/api/v2"

    async def get_headers(self, oauth_token=None):
        return {
            "Accept": "application/json"
        }

    async def get_channel_by_name(self, channel_name: str):
        url = '{}/broadcasts/public?channel_name={}'.format(self.hostname, channel_name)

        return await self.make_get_request(url=url)
