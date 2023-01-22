from typing import List

from aiohttp import ClientResponseError

from api.core import Core


class Trovo(Core):
    def __init__(self):
        super().__init__()
        self.hostname: str = "https://open-api.trovo.live/openplatform"
        self.client_id: str = ""

    async def get_headers(self, oauth_token=None):
        return {
            "Accept": "application/json",
            "Client-ID:": self.client_id
        }

    async def get_user(self, usernames: List[str]):
        url = "{}/getusers".format(self.hostname)
        body = {"user": usernames}

        return await self.make_post_request(url=url, body=body)

    async def get_channel_by_id(self, channel_id: int):
        url = '{}/channels/id'.format(self.hostname)
        body = {
            "channel_id": channel_id
        }

        return await self.make_post_request(url=url, body=body)
