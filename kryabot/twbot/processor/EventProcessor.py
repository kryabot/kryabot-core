import time
from twbot.object.ChatEvent import ChatEvent
from twbot.object.RateEvent import RateEvent
from api.twitch import Twitch
from random import randint


class EventProcessor:

    def __init__(self, silent, logger):
        self.events = []
        self.is_silent = silent
        self.logger = logger
        self.twitch_api = Twitch(None)

    async def process_message(self, irc_data):
        for event in self.events:
            if event.channel_name == irc_data.channel.name and await event.is_active():
                if await event.can_remind() == True:
                    await irc_data.send(event.text)

                if isinstance(event, ChatEvent):
                    if irc_data.message.content.lower() == event.keyword.lower():
                        # Non subs and followers only
                        if event.type == 1 and not irc_data.author.is_subscriber:
                            self.logger.info('[1] Adding participant {}'.format(irc_data.author.name))
                            await event.add(irc_data.author.name)

                        # Subs only
                        if event.type == 2 and irc_data.author.is_subscriber:
                            self.logger.info('[2] Adding participant {}'.format(irc_data.author.name))
                            await event.add(irc_data.author.name)

                        # Any follower
                        if event.type == 3:
                            self.logger.info('[3] Adding participant {}'.format(irc_data.author.name))
                            await event.add(irc_data.author.name)
                elif isinstance(event, RateEvent):
                    if str(irc_data.message.content).isnumeric():
                        await event.check_and_add(irc_data.author.name, irc_data.message.content)

    async def start_rate_event(self, irc_data, runtime):
        i = await self.get_int(runtime)
        if 0 < i < 30:
            i = 30

        try:
            existing_event = await self.find_event(irc_data.channel.name, irc_data.author.name)
            if not existing_event is None:
                if await existing_event.is_active():
                    await irc_data.send('{u} can not start new event - you already have active rate event. Participants: {p}'.format(u=irc_data.author.name, p=len(existing_event.users)))
                    return
                else:
                    self.events.remove(existing_event)

            self.logger.info('RateEvent started on channel {} by {}'.format(irc_data.channel.name, irc_data.author.name))

            event = RateEvent(logger=self.logger)
            event.channel_name = irc_data.channel.name
            event.by = irc_data.author.name
            event.runtime = i
            event.until = event.started + i
            event.last_reminder = time.time()
            event.text = '/me Rate event is ongoing. Send your vote by messaging number between 1-10!'
            self.events.append(event)
            await irc_data.send(event.text)
        except Exception as ex:
            self.logger.error(ex)

    async def start_event(self, irc_data, keyword, runtime, event_type):
        i = await self.get_int(runtime)
        if 0 < i < 30:
            i = 30

        try:
            existing_event = await self.find_event(irc_data.channel.name, irc_data.author.name)
            if not existing_event is None:
                if await existing_event.is_active():
                    await irc_data.send('{u} can not start new event - you already have active event. Participants: {p}, keyword: {k}'.format(u=irc_data.author.name, k=existing_event.keyword, p=len(existing_event.users)))
                    return
                else:
                    self.events.remove(existing_event)

            self.logger.info('Event started on channel {ch} by {u} with keyword {key}'.format(ch=irc_data.channel.name,
                                                                                              u=irc_data.author.name,
                                                                                              key=keyword))
            event = ChatEvent(logger=self.logger)
            event.channel_name = irc_data.channel.name
            event.keyword = keyword
            event.by = irc_data.author.name
            event.users = []
            event.started = time.time()
            event.runtime = i
            event.until = event.started + i
            event.last_reminder = time.time()
            event.type = event_type
            event.active = True
            event.text = await self.get_event_starting_text(event_type)
            event.text = event.text.format(key=keyword)
            self.events.append(event)

            await irc_data.send(event.text)
        except Exception as e:
            self.logger.error("{err}".format(err=str(e)))

    async def get_event_starting_text(self, event_type):
        if event_type == 1:
            return '/me HolidayPresent Ты ноунейм-ансаб и хочешь выиграть подписку? Фолловнись на канал и напиши один раз в чат "{key}", чтобы попасть в список работяг!'
        if event_type == 2:
            return '/me Event started! Write "{key}" to participate in the event! You must be subscriber of the channel to participate!'
        if event_type == 3:
            return '/me Event started! Write "{key}" to participate in the event! You must be follower of the channel to participate!'

        return '/me Event started! Write "{key}" to participate in the event!'

    async def find_event(self, channel_name, author_name):
        for event in self.events:
            if event.channel_name == channel_name and event.by == author_name:
                return event

        return None

    async def finish_event(self, irc_data, channel_twitch_id):
        existing_event = await self.find_event(irc_data.channel.name, irc_data.author.name)
        if existing_event is None:
            return

        if isinstance(existing_event, ChatEvent):
            await self.finish_chat_event(existing_event, irc_data, channel_twitch_id)
        elif isinstance(existing_event, RateEvent):
            await self.finish_rate_event(existing_event, irc_data, channel_twitch_id)

    async def finish_rate_event(self, existing_event, irc_data, channel_twitch_id):
        try:
            existing_event.active = False
            rate = existing_event.get_avg()
            info_text = ' [Started by {by}, participants: {total}]'.format(by=existing_event.by, total=len(existing_event.users.keys()))
            await irc_data.send('/me HSWP Rating finished. Result is: {} {info}'.format(rate, info=info_text))
            self.events.remove(existing_event)
        except Exception as e:
            self.logger.error(e)

    async def finish_chat_event(self, existing_event, irc_data, channel_twitch_id):
        try:
            while True:
                winner = await existing_event.roll_user()

                if winner is None:
                    await irc_data.send('No participants...  SMOrc')
                    return

                # Follower check, if false reroll
                if existing_event.type in [1,3] and not await self.is_follower(channel_twitch_id, winner):
                    self.logger.info('Event by: {by}, channel: {ch}. Rolled {winner}, but not a follower. Rerolling.'.format(winner=winner, by=existing_event.by, ch=existing_event.channel_name))
                    continue

                break

            text = await self.random_event_text(existing_event.type)
            info_text = ' [Started by {by}, participants: {total}]'.format(by=existing_event.by, total=(len(existing_event.users) + 1))
            self.logger.info('Event by {by} on channel {ch} finished. winner is {win}. Total participants: {total}'.format(by=existing_event.by, ch=existing_event.channel_name, win=winner, total=(len(existing_event.users) + 1)))
            await irc_data.send('{winner} {text} {info}'.format(winner=winner, text=text, info=info_text))

        except Exception as e:
            self.logger.error("{err}".format(err=str(e)))

    async def random_event_text(self, event_type):
        list = []
        if event_type == 1:
            list.append(' ТЫ ПОБЕДИЛ! Теперь ты проклят! Потеряешь все ноль друзей и на всегда будешь один! olyashLove')
            list.append(' ГОООООООЛ olyashLove')
            list.append(' сожалею но тебе придется сесть на бутылку olyashLove')
            list.append(' ТЫ ПОБЕДИЛ! Теперь у тебя есть самые крутые смайлики на твиче olyashGasm')
        if event_type == 2:
            list.append(' has won!')

        if len(list) == 0:
            list.append(' you have won! <3 ')

        idx = randint(0, len(list) - 1)
        return list[idx]


    async def is_follower(self, channel_id, username)-> bool:
        try:
            user_data = await self.twitch_api.get_user_by_name(username)
            follower_check = await self.twitch_api.check_channel_following(channel_id, user_data['users'][0]['_id'])
            return True
        except Exception as e:
            # 404 is returned if not follower
            return False

    async def cancel_event(self, irc_data):
        try:
            existing_event = await self.find_event(irc_data.channel.name, irc_data.author.name)
            if existing_event is None:
                return

            self.events.remove(existing_event)
        except Exception as e:
            self.logger.error("{err}".format(err=str(e)))

    async def delete_user_events(self, channel_name, by):

        pass

    async def delete_channel_events(self, channel_name):
        pass

    async def get_int(self, val)-> int:
        try:
            return int(val)
        except:
            return 0