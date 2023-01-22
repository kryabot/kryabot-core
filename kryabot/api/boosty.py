from api.core import Core


class Boosty(Core):
    def __init__(self):
        super().__init__()
        self.base = 'https://api.boosty.to/v1/blog'

    async def get_user_posts(self, user: str, limit: int=5, offset: str=None):
        # https://api.boosty.to/v1/blog/olyashaa/post/?limit=5
        url = '{}/{}/post/?limit={}'.format(self.base, user, limit)

        if offset:
            url = '{}&offset={}'.format(url, offset)

        return await self.make_get_request(url)