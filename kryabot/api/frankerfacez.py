from aiohttp import ClientResponseError

from api.core import Core


class Frankerfacez(Core):
    def __init__(self, cfg=None):
        super().__init__(cfg=cfg)

    async def get_channel_emotes(self, channel_name):
        url = 'https://api.frankerfacez.com/v1/room/{}'.format(channel_name)
        try:
            return await self.make_get_request(url=url)
        except ClientResponseError as ex:
            if ex.status == 404:
                return None
            raise ex
