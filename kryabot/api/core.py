import asyncio
import aiohttp
from aiohttp import ClientResponseError, ClientConnectorError, ClientTimeout
import logging
from object.BotConfig import BotConfig
import async_timeout
import io


class Core:
    def __init__(self):
        self.logger = logging.getLogger('krya.api')
        self.max_retries = 5
        self.initial_backoff = 0.5
        self.cfg = BotConfig.get_instance()
        self.default_session_timeout = 30
        self.default_client_timeout = ClientTimeout(total=self.default_session_timeout)

    async def get_headers(self, oauth_token=None):
        return {}

    def _get_rate_limits(self, response) -> str:
        rate_limit = response.headers.get('Ratelimit-Limit', None)
        rate_remaining = response.headers.get('Ratelimit-Remaining', None)
        rate_info = ''
        if rate_limit and rate_remaining:
            rate_info = 'RateLimits({}/{})'.format(rate_remaining, rate_limit)

        return rate_info

    async def make_get_request(self, url, token=None, headers=None, params=None):
        if headers is None:
            headers = await self.get_headers(token)

        last_exception = None
        for i in range(self.max_retries):
            try:
                async with aiohttp.ClientSession(headers=headers, timeout=self.default_client_timeout) as session:
                    async with session.get(url, params=params) as response:
                        rate_info = self._get_rate_limits(response)

                        self.logger.info('[GET] {sta} {url} ({params}) {rates} [retries: {i}]'.format(sta=response.status, url=url, i=i, params=params, rates=rate_info))

                        # Retry if failed
                        if response.status >= 500 or response.status == 429:
                            await asyncio.sleep(self.initial_backoff * 2 * (i + 1))
                            continue

                        if not await self.is_success(response):
                            continue

                        try:
                            resp_data = await response.json()
                        except Exception as err:
                            resp_data = None

                        return resp_data
            except asyncio.exceptions.TimeoutError as ex:
                last_exception  = ex
                self.logger.info('[GET] {sta} {url} [{i}]'.format(sta='TimeoutError', url=url, i=i))
                continue

        self.logger.error('All retries failed for {url}'.format(url=url))
        if last_exception:
            raise last_exception
        return None

    async def make_post_request(self, url, token=None, body=None, headers=None, params=None):
        if headers is None:
            headers = await self.get_headers(token)

        async with aiohttp.ClientSession(headers=headers) as session:
            for i in range(self.max_retries):
                async with session.post(url, params=params, json=body) as response:
                    rate_info = self._get_rate_limits(response)

                    self.logger.info('[POST] {sta} {url} ({params}) {rates} [retries: {i}]'.format(sta=response.status, url=url, i=i, params=params, rates=rate_info))

                    # Retry if failed
                    if response.status >= 500:
                        await asyncio.sleep(self.initial_backoff * 2 * (i + 1))
                        continue

                    if not await self.is_success(response):
                        continue

                    return await response.json(content_type=None)
            self.logger.error('All retries failed for {url}'.format(url=url))
            return None

    async def make_patch_request(self, url, token=None, body=None, headers=None, params=None):
        if headers is None:
            headers = await self.get_headers(token)

        async with aiohttp.ClientSession(headers=headers) as session:
            for i in range(self.max_retries):
                async with session.patch(url, params=params, json=body) as response:
                    rate_info = self._get_rate_limits(response)

                    self.logger.info('[PATCH] {sta} {url} ({params}) {rates} [retries: {i}]'.format(sta=response.status, url=url, i=i, params=params, rates=rate_info))

                    # Retry if failed
                    if response.status >= 500:
                        await asyncio.sleep(self.initial_backoff * 2 * (i + 1))
                        continue

                    if not await self.is_success(response):
                        continue

                    return await response.json(content_type=None)
            self.logger.error('All retries failed for {url}'.format(url=url))
            return None

    async def make_put_request(self, url, token=None, body=None, headers=None, params=None):
        if headers is None:
            headers = await self.get_headers(token)

        async with aiohttp.ClientSession(headers=headers) as session:
            for i in range(self.max_retries):
                async with session.put(url, params=params, json=body) as response:
                    rate_info = self._get_rate_limits(response)

                    self.logger.info('[PUT] {sta} {url} ({params}) {rates} [retries: {i}]'.format(sta=response.status, url=url, i=i, params=params, rates=rate_info))

                    # Retry if failed
                    if response.status >= 500:
                        await asyncio.sleep(self.initial_backoff * 2 * (i + 1))
                        continue

                    if not await self.is_success(response):
                        continue

                    return await response.json(content_type=None)
            self.logger.error('All retries failed for {url}'.format(url=url))
            return None

    async def make_post_request_data(self, url, token=None, body=None, headers=None, params=None):
        if headers is None:
            headers = await self.get_headers(token)

        async with aiohttp.ClientSession(headers=headers) as session:
            for i in range(self.max_retries):
                async with session.post(url, data=body) as response:
                    rate_info = self._get_rate_limits(response)
                    self.logger.info('[POST] {sta} {url} ({params}) {rates} [retries: {i}]'.format(sta=response.status, url=url, i=i, params=params, rates=rate_info))

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

    async def make_delete_request_data(self, url, token=None, body=None, headers=None, params=None):
        if headers is None:
            headers = await self.get_headers(token)

        async with aiohttp.ClientSession(headers=headers) as session:
            for i in range(self.max_retries):
                async with session.delete(url, data=body, params=params) as response:
                    rate_info = self._get_rate_limits(response)
                    self.logger.info('[DELETE] {sta} {url} ({params}) {rates} [retries: {i}]'.format(sta=response.status, url=url, i=i, params=params, rates=rate_info))

                    # Retry if failed
                    if response.status >= 500:
                        await asyncio.sleep(self.initial_backoff * 2 * ( i + 1 ))
                        continue

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
            body = await response.json()
        except:
            body = ''

        try:
            response.raise_for_status()
        except ClientConnectorError as e:
            self.logger.error('[{method}] {reason} {body}'.format(reason=str(e), method=response.method, body=body))
            if e.host == 'api.twitch.tv':
                await asyncio.sleep(30)
            else:
                await asyncio.sleep(10)
            return False
        except ClientResponseError as e:
            try:
                body = await response.json()
            except:
                body = ''
            self.logger.error('[{method}] {reason} {body}'.format(reason=e.message, method=e.request_info.method, body=body))
            raise e

        return True
