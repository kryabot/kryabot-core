from api.core import Core


class Instagram(Core):
    def __init__(self):
        super().__init__()

    async def get_story_by_id(self, session_key, instagram_user_id):
        headers = {
            'user-agent': 'Instagram 10.26.0 (iPhone7,2; iOS 10_1_1; en_US; en-US; scale=2.00; gamut=normal; 750x1334) AppleWebKit/420+',
            'cookie': session_key,
        }
        url = 'https://i.instagram.com/api/v1/feed/user/{}/story/'.format(instagram_user_id)
        return await self.make_get_request(url=url, headers=headers)

    async def get_stories(self, session_key, user):
        id = await self.get_user_id(user)
        return await self.get_story_by_id(session_key, id)

    async def get_user(self, username):
        url = 'https://www.instagram.com/{}/?__a=1'.format(username)
        return await self.make_get_request(url=url)

    async def get_user_id(self, username):
        user = await self.get_user(username)
        # TODO: cache

        return user['graphql']['user']['id']