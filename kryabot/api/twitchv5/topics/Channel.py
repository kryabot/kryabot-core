from abc import ABC

from api.twitchv5.TopicInterface import TopicInterface
from utils.twitch import broadcaster_auth, pagination


class Channel(TopicInterface, ABC):
    @broadcaster_auth()
    @pagination(first=100)
    async def get_vips(self, broadcaster_id: int, token: str, user_id: int = None, first: int = 100, after: str = None):
        """
        https://dev.twitch.tv/docs/api/reference#get-vips

        :param broadcaster_id:
        :param token:
        :param user_id:
        :param first:
        :param after:
        :return:
        """

        params = [
            ("broadcaster_id", broadcaster_id),
            ("first", first),
        ]

        if user_id:
            params.append(("user_id", user_id))

        if after:
            params.append(("after", after))

        url = '{}channels/vips'.format(self.hostname)
        headers = await self.get_json_headers(bearer_token=token)
        return await self.make_get_request(url=url, headers=headers, params=params)

    @broadcaster_auth()
    async def add_vip(self, broadcaster_id: int, token: str, user_id: int):
        """
        https://dev.twitch.tv/docs/api/reference#add-channel-vip

        :param broadcaster_id:
        :param token:
        :param user_id:
        :return:
        """

        params = [
            ("broadcaster_id", broadcaster_id),
            ("user_id", user_id),
        ]

        url = '{}channels/vips'.format(self.hostname)
        headers = await self.get_json_headers(bearer_token=token)
        return await self.make_post_request(url=url, headers=headers, params=params)

    @broadcaster_auth()
    async def remove_vip(self, broadcaster_id: int, token: str, user_id: int):
        """
        https://dev.twitch.tv/docs/api/reference#remove-channel-vip

        :param broadcaster_id:
        :param token:
        :param user_id:
        :return:
        """

        params = [
            ("broadcaster_id", broadcaster_id),
            ("user_id", user_id),
        ]

        url = '{}channels/vips'.format(self.hostname)
        headers = await self.get_json_headers(bearer_token=token)
        return await self.make_delete_request_data(url=url, headers=headers, params=params)

    @broadcaster_auth()
    async def get_channel_subs(self, broadcaster_id: int, token: str,  users: [int] = None, after=None, first: int = 20):
        """
        https://dev.twitch.tv/docs/api/reference#get-broadcaster-subscriptions

        :param broadcaster_id:
        :param token:
        :param users:
        :param after:
        :param first:
        :return:
        """
        params = [('broadcaster_id', broadcaster_id)]

        if users:
            if len(users) > 100:
                raise ValueError("Cannot request more than 100 users! (current size={})".format(len(users)))

            first = len(users)
            for user in users:
                params.append(('user_id', str(user)))

        if after:
            params.append(('after', after))
        if first:
            params.append(('first', str(first)))

        url = '{helix}subscriptions'.format(helix=self.hostname)

        headers = await self.get_json_headers(bearer_token=token)
        return await self.make_get_request(url, headers=headers, params=params)

    @broadcaster_auth()
    async def get_editors(self, broadcaster_id: int, token: str):
        """
        https://dev.twitch.tv/docs/api/reference#get-channel-editors

        :param broadcaster_id:
        :param token:
        :return:
        """

        params = [('broadcaster_id', broadcaster_id)]
        url = '{}channels/editors'.format(self.hostname)
        headers = await self.get_json_headers(bearer_token=token)

        return await self.make_get_request(url, headers=headers, params=params)
