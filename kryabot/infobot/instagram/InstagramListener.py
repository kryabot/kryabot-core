import asyncio
from typing import List
from datetime import datetime

from instaloader import Instaloader

from infobot.instagram.InstagramEvents import InstagramPostEvent, InstagramStoryEvent
from infobot.instagram.InstagramProfile import InstagramProfile
from infobot.Listener import Listener
from infobot.async_util import run_in_executor
import instaloader
from sqlite3 import connect


class InstagramListener(Listener):
    def __init__(self, manager):
        super().__init__(manager)
        self.instagram: Instaloader = instaloader.Instaloader()
        self.instagram.dirname_pattern = "cache"
        self.profiles: List[InstagramProfile] = []

    async def start(self):
        await super().start()
        await self.login()
        self.period = 300

    @Listener.repeatable
    async def listen(self):
        self.logger.debug('Checking instagram data')

        self.listen_posts()
        self.listen_stories()
        #await asyncio.wait([self.listen_posts(), self.listen_stories()])
        # self.loop.create_task()
        # self.loop.create_task()

    def recreate_session_from_firefox(self):
        SESSION_FILE = "C:/Users/Oskar/AppData/Roaming/Mozilla/Firefox/Profiles/t7kskj56.default/cookies.sqlite"
        self.instagram = Instaloader(max_connection_attempts=1)
        self.instagram.context._session.cookies.update(connect(SESSION_FILE).execute("SELECT name, value FROM moz_cookies WHERE host='.instagram.com'"))
        username = self.instagram.test_login()
        self.instagram.context.username = username
        self.instagram.save_session_to_file('instaloader-session-' + username)

    def force_login(self):
        self.instagram.login(self.cfg.getConfig()['INSTAGRAM']['login'], self.cfg.getConfig()['INSTAGRAM']['password'])
        self.instagram.save_session_to_file()

    def session_login(self):
        self.instagram.load_session_from_file(self.cfg.getConfig()['INSTAGRAM']['login'], filename='instaloader-session-' + self.cfg.getConfig()['INSTAGRAM']['login'])

    @run_in_executor
    def login(self):
        try:
            print('trying session login')
            self.session_login()
        except Exception as e:
            print(str(e))
            print('reimporting session')
            #self.force_login()
            self.recreate_session_from_firefox()
            self.session_login()

        self.logger.info('Instagram login successful')

    @run_in_executor
    def listen_posts(self):
        self.logger.debug('Checking instagram posts')

        for profile in self.profiles:
            for post in self.instagram.check_profile_id(profile.instagram_name).get_posts():
                if profile.post_exists(str(post.mediaid)):
                    break

                profile.last_post_id = post.mediaid
                event = InstagramPostEvent(profile)
                event.add_post(post)
                self.logger.debug('Created new instagram post event')
                self.loop.create_task(self.manager.event(event))

                if profile.is_first_bot_post():
                    break


    @run_in_executor
    def listen_stories(self):
        self.logger.debug('Checking instagram stories')

        for profile in self.profiles:
            instagram_profile = self.instagram.check_profile_id(profile.instagram_name)
            for story in self.instagram.get_stories([instagram_profile.userid]):
                self.logger.debug('Created new instagram story event')
                event = InstagramStoryEvent(profile)
                event.add_story(story)

                if event.is_new():
                    self.loop.create_task(self.manager.event(event))
                else:
                    break

    async def update_data(self, start: bool = False)->None:
        self.logger.info('Updating instagram listener data')

        try:
            profiles = await self.db.getInstagramProfiles()
            history = await self.db.getInstagramHistory()

            self.logger.debug('profiles: {}'.format(profiles))
            self.logger.debug('history: {}'.format(history))

            await self.update_profiles(profiles, history)
        except Exception as ex:
            self.logger.exception(ex)

    def get_new_profile_instance(self, *args, **kwargs):
        return InstagramProfile(*args, **kwargs)