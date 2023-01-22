from abc import ABC

from api.twitchv5.TopicInterface import TopicInterface
from utils.twitch import app_auth


class Stream(TopicInterface, ABC):
    async def get_streams(self, first=20, channel_name=None, after=None, before=None, language=None):
        url = '{base}streams?first={id}'.format(base=self.hostname, id=first)

        if channel_name is not None:
            url = '{eurl}&user_login={ulog}'.format(eurl=url, ulog=channel_name)

        if after is not None:
            url = '{eurl}&after={valafter}'.format(eurl=url, valafter=after)

        if before is not None:
            url = '{eurl}&before={valbefore}'.format(eurl=url, valbefore=before)

        if language is not None:
            url = '{eurl}&language={lang}'.format(eurl=url, lang=language)

        return await self.make_get_request(url)

    @app_auth()
    async def get_stream_info_by_ids(self, twitch_user_ids, first=None, after=None, before=None):
        url = '{base}streams'.format(base=self.hostname)

        params = [('user_id', x) for x in twitch_user_ids]
        if len(twitch_user_ids) == 0:
            raise ValueError('Must provide atleast one id')

        if len(twitch_user_ids) > 100:
            raise ValueError('Cannot request more than 100 ids at once')

        first = len(twitch_user_ids)
        if first is not None:
            params.append(('first', first))
        if after is not None:
            params.append(('after', after))
        if before is not None:
            params.append(('before', before))

        return await self.make_get_request(url=url, params=params)
