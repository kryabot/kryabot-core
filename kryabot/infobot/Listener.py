import functools
from datetime import datetime
from logging import Logger

from infobot.Profile import Profile
from infobot.UpdateBuilder import InfoBotUpdate
from object.Database import Database
from object.ApiHelper import ApiHelper

import asyncio


class Listener:
    def __init__(self, manager):
        self.logger: Logger = manager.logger if manager else Logger('default')
        self.loop = asyncio.get_event_loop()
        self.cfg = manager.cfg if manager else None
        self.api: ApiHelper = manager.api if manager else None
        self.db: Database = manager.db if manager else None
        self.period: int = 30
        self.manager = manager
        self.update_type = InfoBotUpdate
        self.profiles = None

    async def start(self)->None:
        await self.update_data(start=True)

    async def update_data(self, start: bool = False)->None:
        """
        This method is called when need to update data from database.
        Implement needed database calls and call update_profiles
        :param start:
        :return:
        """

        pass

    async def listen(self)->None:
        """
        This method is called periodically, implement main checking logic here
        `period` property defines how ofter it is called

        :return:
        """
        pass

    async def sleep(self, sleep_time: int=None)->None:
        """
        Little wrapper for asyncio sleep. Used to sleep between `listen()` method calls

        :return:
        """
        if sleep_time is None:
            sleep_time = self.period

        await asyncio.sleep(sleep_time)

    async def push_update(self, data):
        if isinstance(data, self.update_type):
            await self.on_update(data)

    async def on_update(self, data):
        pass

    @classmethod
    def repeatable(cls, f):
        @functools.wraps(f)
        async def inner(self, *args, **kwargs):
            first = True
            while True:
                try:
                    if not first:
                        await self.sleep()

                    first = False
                    await f(self, *args, **kwargs)
                except Exception as ex:
                    await self.manager.on_exception(ex)

        return inner

    async def remove_profile(self, profile: Profile):
        self.profiles.remove(profile)

    def has_link(self, profile) -> bool:
        for link in self.manager.links.links:
            if link.link_table == profile.link_table and link.link_id == profile.profile_id:
                return True

        return False

    async def update_profiles(self, profiles, histories, start: bool=False):
        """
        Main logic how profiles are stored in profile list.
        Method `handle_new_profile()` is called when new profile appears after start

        :param profiles:
        :param histories:
        :param start:
        :return:
        """
        update_ts = datetime.now()

        for row in profiles:
            next_row = False

            for existing_profile in self.profiles:
                if existing_profile.profile_id == int(row[existing_profile.profile_id_key]):
                    existing_profile.update(row, update_ts)
                    next_row = True
                    break

            if next_row:
                continue

            profile = self.get_new_profile_instance(row, update_ts)
            profile.set_history(histories)
            await profile.restore_from_cache(self.manager.db.redis)
            self.profiles.append(profile)
            if not start:
                await self.handle_new_profile(profile)

        # Remove deleted profile
        self.profiles = [profile for profile in self.profiles if not profile.outdated(update_ts)]

    def get_new_profile_instance(self, *args, **kwargs)->Profile:
        """
        Override to return needed profile instance. Is used during data update from database

        Example:
        `
        def get_new_profile_instance(self, *args, **kwargs):
            return TwitchProfile(*args, **kwargs)
        `

        :param args:
        :param kwargs:
        :return:
        """
        raise NotImplementedError('Method Listener.get_new_profile must be overridden')

    async def handle_new_profile(self, profile: Profile):
        """
        Called in data update from database when new profile appears after start up.
        Method not called during first data update (start)

        :param profile:
        :return:
        """
        pass
