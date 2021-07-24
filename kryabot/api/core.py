import asyncio
import aiohttp
from aiohttp import ClientResponseError, ClientConnectorError, ClientTimeout
import logging
from object.BotConfig import BotConfig
import async_timeout
import io


class Core:
    def __init__(self, cfg=None):
        self.logger = logging.getLogger('krya.api')
        self.max_retries = 3
        self.initial_backoff = 0.5
        if cfg is None:
            cfg = BotConfig()
        self.cfg = cfg
        self.default_session_timeout = 30
        self.default_client_timeout = ClientTimeout(total=self.default_session_timeout)

    async def get_headers(self, oauth_token=None):
        return {}

    async def make_get_request(self, url, token=None, headers=None, params=None):
        if headers is None:
            headers = await self.get_headers(token)

        for i in range(self.max_retries):
            try:
                async with aiohttp.ClientSession(headers=headers, timeout=self.default_client_timeout) as session:
                    async with session.get(url, params=params) as response:
                        self.logger.info('[GET] {sta} {url} [{i}]'.format(sta=response.status, url=url, i=i))
                        # Retry if failed
                        if response.status >= 500:
                            await asyncio.sleep(self.initial_backoff * 2 * (i + 1))
                            continue

                        if not await self.is_success(response):
                            continue

                        try:
                            resp_data = await response.json()
                        except Exception as err:
                            resp_data = None

                        return resp_data
            except asyncio.exceptions.TimeoutError:
                self.logger.info('[GET] {sta} {url} [{i}]'.format(sta='TimeoutError', url=url, i=i))
                continue

        self.logger.error('All retries failed for {url}'.format(url=url))
        return None

    async def make_post_request(self, url, token=None, body=None, headers=None):
        if headers is None:
            headers = await self.get_headers(token)

        async with aiohttp.ClientSession(headers=headers) as session:
            for i in range(self.max_retries):
                async with session.post(url, json=body) as response:
                    # Retry if failed
                    if response.status >= 500:
                        await asyncio.sleep(self.initial_backoff * 2 * (i + 1))
                        continue

                    self.logger.info('[POST] {sta} {url}'.format(sta=response.status, url=url))

                    if not await self.is_success(response):
                        continue

                    return await response.json(content_type=None)
            self.logger.error('All retries failed for {url}'.format(url=url))
            return None

    async def make_post_request_data(self, url, token=None, body=None, headers=None):
        if headers is None:
            headers = await self.get_headers(token)

        async with aiohttp.ClientSession(headers=headers) as session:
            for i in range(self.max_retries):
                async with session.post(url, data=body) as response:
                    # Retry if failed
                    if response.status >= 500:
                        await asyncio.sleep( self.initial_backoff * 2 * ( i + 1 ))
                        continue

                    self.logger.info('[POST] {sta} {url}'.format(sta=response.status, url=url))
                    if not await self.is_success(response):
                        continue

                    return await response.json(content_type=None)
            self.logger.error('All retries failed for {url}'.format(url=url))
            return None

    async def download_file_io(self, url, token=None, body=None, headers=None):
        if headers is None:
            headers = await self.get_headers(token)

        file = io.BytesIO()
        async with async_timeout.timeout(240):
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(url) as response:
                    async for data in response.content.iter_chunked(1024):
                        file.write(data)

        return file

    async def is_success(self, response)->bool:

        try:
            response.raise_for_status()
        except ClientConnectorError as e:
            self.logger.error('[GET] {reason}'.format(reason=str(e)))
            if e.host == 'api.twitch.tv':
                await asyncio.sleep(30)
            else:
                await asyncio.sleep(10)
            return False
        except ClientResponseError as e:
            self.logger.error('[GET] {reason}'.format(reason=e.message))
            raise e

        return True
