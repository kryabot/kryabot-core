from aiohttp import ClientResponseError

from api.core import Core


class Betterttv(Core):
    def __init__(self, cfg=None):
        super().__init__(cfg=cfg)

    async def get_global_emotes(self):
        url = 'https://api.betterttv.net/3/cached/emotes/global'
        return await self.make_get_request(url=url)

    async def get_channel_emotes(self, channel_name: str):
        url = 'https://api.betterttv.net/2/channels/{}'.format(channel_name)
        try:
            return await self.make_get_request(url=url)
        except ClientResponseError as ex:
            if ex.status == 404:
                return None
            raise ex