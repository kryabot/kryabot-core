from abc import ABC

from api.twitchv5.TopicInterface import TopicInterface


class User(TopicInterface, ABC):
    async def get_users(self, ids: [int] = None, usernames: [str] = None, skip_cache: bool = False):
        if ids is None and usernames is None:
            raise ValueError('Bad input - missing ids or usernames value')

        response = {'data': []}
        params = []

        # Check ID list
        if ids is not None and len(ids) > 0:
            for idx in ids:
                data = None
                if self.redis is not None and not skip_cache:
                    data = await self.redis.get_parsed_value_by_key(self.redis_keys.get_api_tw_user_by_id(idx))

                if data is None:
                    params.append(('id', idx))
                else:
                    response['data'].append(data)

        # Check username list
        if usernames is not None and len(usernames) > 0:
            for username in usernames:
                data = None
                if self.redis is not None and not skip_cache:
                    data = await self.redis.get_parsed_value_by_key(self.redis_keys.get_api_tw_user_by_name(username))

                if data is None:
                    params.append(('login', username))
                else:
                    response['data'].append(data)

        if len(params) > 100:
            raise ValueError('Cannot request more than 100 entries at once (current size={})'.format(len(params)))

        # After checking cache, we still have requests to do
        if len(params) > 0:
            url = '{helix}users'.format(helix=self.hostname)
            headers = await self.get_json_headers(add_auth=False)
            twitch_response = await self.make_get_request(url, headers=headers, params=params)
            if twitch_response is not None and 'data' in twitch_response:
                for item in twitch_response['data']:
                    # Add to cache
                    if self.redis is not None:
                        await self.redis.set_parsed_value_by_key(self.redis_keys.get_api_tw_user_by_id(item['id']), item,
                                                                 expire=self.redis_keys.ttl_half_day)
                        await self.redis.set_parsed_value_by_key(self.redis_keys.get_api_tw_user_by_name(item['login']), item,
                                                                 expire=self.redis_keys.ttl_half_day)

                    # Add to return value
                    response['data'].append(item)

        return response

    async def get_user_follows(self, channel_id: int, users: [int] = None, first: int = 20, after=None, token=None):
        params = [('to_id', str(channel_id))]

        if users:
            if len(users) > 99:
                raise ValueError("Cannot request more than 100 users! (current size={})".format(len(users)))

            first = len(users)
            for user in users:
                params.append(('from_id', str(user)))

        if after:
            params.append(('after', after))
        if first:
            params.append(('first', str(first)))

        url = '{}users/follows'.format(self.hostname)
        return await self.make_get_request(url, params=params)

    async def check_channel_following(self, channel_id, user_id):
        url = '{helix}users/follows?from_id={uid}&to_id={cid}'.format(helix=self.hostname, uid=user_id, cid=channel_id)
        return await self.make_get_request(url)
