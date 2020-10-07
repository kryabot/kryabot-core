from api.core import Core


class Instagram(Core):
    def __init__(self, cfg=None):
        super().__init__(cfg=cfg)
        self.session_key = 'ds_user_id=2308951415&amp;sessionid=2308951415%3Af20N33AgeREZPa%3A22'

    async def get_story_by_id(self, instagram_user_id):
        headers = {
            'user-agent': 'Instagram 10.26.0 (iPhone7,2; iOS 10_1_1; en_US; en-US; scale=2.00; gamut=normal; 750x1334) AppleWebKit/420+',
            'cookie': self.session_key,
        }
        url = 'https://i.instagram.com/api/v1/feed/user/{}/story/'.format(instagram_user_id)
        return await self.make_get_request(url=url, headers=headers)

    async def get_stories(self, user):
        id = await self.get_user_id(user)
        return await self.get_story_by_id(id)

    async def get_user(self, username):
        url = 'https://www.instagram.com/{}/?__a=1'.format(username)
        return await self.make_get_request(url=url)

    async def get_user_id(self, username):
        user = await self.get_user(username)
        # TODO: cache

        return user['graphql']['user']['id']