from api.core import Core


class VK(Core):
    def __init__(self, cfg=None):
        super().__init__(cfg=cfg)
        self.session_key = self.cfg.getVKConfig()['SESSION']
        self.vk_version = '5.74'

    async def get_song(self, user):
        url = 'https://api.vk.com/method/users.get?user_ids={u}&access_token={token}&v={v}&fields=status'.format(token=self.session_key, u=user, v=self.vk_version)
        return await self.make_get_request(url=url)
