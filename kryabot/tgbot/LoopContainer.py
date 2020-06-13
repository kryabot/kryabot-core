import asyncio
import logging
from datetime import datetime, timedelta
from object.BotConfig import BotConfig
from tgbot.AuthBot import AuthBot
from tgbot.KryaClient import KryaClient
from webserver.WebHandler import WebHandler


class LoopContainer:
    def __init__(self):
        self.guard_bot: KryaClient = None
        self.auth_bot: AuthBot = None
        self.web_app: WebHandler = None
        self.loop = asyncio.get_event_loop()
        self.logger: logging.Logger = logging.getLogger('krya.tg')
        self.cfg = BotConfig()
        self.logger.info('LoopContainer initiated')

    async def start(self):
        self.logger.info('Starting auth bot...')
        bot = AuthBot(loop=self.loop, cfg=self.cfg)
        await bot.run()

        self.logger.info('Starting guard bot...')
        self.guard_bot = KryaClient(loop=self.loop, logger=self.logger, cfg=self.cfg)
        await self.guard_bot.start_bot()

        self.logger.info('Starting web handler...')
        self.web_app = WebHandler(self.loop, cfg=self.cfg)
        await self.web_app.start(self.guard_bot)

        self.logger.info('All services started')

    async def run(self):
        tasks = []
        tasks.append(self.guard_bot.run_until_disconnected())
        tasks.append(self.daily_tasks_utc18())
        tasks.append(self.daily_tasks_utc17())
        await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED, loop=self.loop)

        print('run failed')

    async def stop(self):
        pass

        # try:
        #     await self.guard_bot.disconnect()
        # except Exception as ex:
        #     pass
        #
        # try:
        #     await self.auth_bot.disconnect()
        # except Exception as ex:
        #     pass
        #
        # try:
        #     # Kills loop
        #     await self.web_app.stop()
        # except Exception as ex:
        #     pass

    # TODO use schedule libs to schedule things, or write proper decorator
    async def daily_tasks_utc18(self):
        while True:
            try:
                now = datetime.utcnow()
                runtime = datetime(now.year, now.month, now.day, 18, 0)
                diff = runtime - now
                if diff.seconds > 120:
                    self.logger.info('Going to sleep for {sec}'.format(sec=diff.seconds))
                    await asyncio.sleep(diff.seconds)
                    continue

                self.logger.info('Starting daily tasks (21)')
                await self.guard_bot.event_user_statistics()

            except Exception as e:
                await self.guard_bot.exception_reporter(e, 'Error during daily task:')

    # TODO use schedule libs to schedule things, or write proper decorator
    async def daily_tasks_utc17(self):
        while True:
            try:
                now = datetime.utcnow()
                runtime = datetime(now.year, now.month, now.day, 17, 0)
                diff = runtime - now
                if diff.seconds > 120:
                    self.logger.info('Going to sleep for {sec}'.format(sec=diff.seconds))
                    await asyncio.sleep(diff.seconds)
                    continue

                self.logger.info('Starting daily tasks (20)')
                await self.guard_bot.update_data()

                for channel in await self.guard_bot.db.get_auth_subchats():
                    if channel['tg_chat_id'] == 0:
                        continue

                    if int(channel['auto_mass_kick']) > 0:
                        next_mass_kick = channel['last_auto_kick'] + timedelta(days=channel['auto_mass_kick'])
                        self.logger.info(
                            'Next planned auto mass kick for channel {chn}: {dt}'.format(chn=channel['channel_name'],
                                                                                         dt=str(next_mass_kick)))

                        if now > next_mass_kick - timedelta(hours=6):
                            self.logger.info(
                                'Starting automated mass kick for channel {chn}'.format(chn=channel['channel_name']))
                            await self.guard_bot.report_to_monitoring(
                                '[Daily] Starting automated mass kick for channel {chn}'.format(
                                    chn=channel['channel_name']))
                            params = []
                            params.append({'key': 'not_verified', 'enabled': 1})
                            params.append({'key': 'not_sub', 'enabled': channel['join_sub_only']})
                            params.append({'key': 'not_follower', 'enabled': channel['join_follower_only']})
                            params.append({'key': 'not_active', 'enabled': 1})
                            try:
                                await self.guard_bot.run_channel_refresh(channel, True, params)
                                next_date = datetime(now.year, now.month, now.day, 20, 00)
                                await self.guard_bot.db.updateAutoMassKickTs(channel['channel_subchat_id'], next_date)
                            except Exception as err:
                                await self.guard_bot.exception_reporter(err, '20 daily task for {}'.format(
                                    channel['channel_name']))
                        else:
                            self.logger.info('Skipping automated mass kick, too early')
                    await asyncio.sleep(10)
            except Exception as e:
                await self.guard_bot.report_exception(e, 'Error during daily task:')