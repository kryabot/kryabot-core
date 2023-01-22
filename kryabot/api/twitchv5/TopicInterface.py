from abc import ABC, abstractmethod


class TopicInterface(ABC):
    @property
    @abstractmethod
    def hostname(self):
        raise NotImplementedError

    @property
    @abstractmethod
    def redis(self):
        raise NotImplementedError

    @property
    @abstractmethod
    def redis_keys(self):
        raise NotImplementedError

    @abstractmethod
    async def get_headers(self, oauth_token=None):
        raise NotImplementedError

    @abstractmethod
    async def get_json_headers(self, oauth_token=None, bearer_token=None, add_auth=True):
        raise NotImplementedError

    @abstractmethod
    async def make_get_request(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    async def make_patch_request(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    async def make_post_request(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    async def make_delete_request_data(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    async def make_put_request(self, *args, **kwargs):
        raise NotImplementedError
