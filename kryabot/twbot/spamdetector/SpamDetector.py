import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from unidecode import unidecode

from object.ApiHelper import ApiHelper
from object.Database import Database
import utils.redis_key as redis_key

MIN_WORDS = 5
INTERVAL_CHECK = 30
MATCH_THRESHOLD = 0.4
MPS_RATIO = 5

SKIP_LIST = ['jesusavgn']
LIST_NAME_BANNED_WORDS = 'spambot_banned_words'
BANNED_WORDS = []

loop = asyncio.get_event_loop()
db = Database(loop, 1)
api = ApiHelper(redis=db.redis)
logger = logging.getLogger('krya.spam')
bttv_global = None

def get_cosine_sim(*strs):
    vectors = [t for t in get_vectors(*strs)]
    return cosine_similarity(vectors)

def get_vectors(*strs):
    text = [t for t in strs]
    vectorizer = CountVectorizer(input=text)
    vectorizer.fit(text)
    return vectorizer.transform(text).toarray()

def parse_fz_emotes(response):
    if response is None:
        return None

    if 'room' not in response or 'set' not in response['room'] or 'sets' not in response:
        return None

    id = response['room']['set']
    if str(id) not in response['sets']:
        return None

    if 'emoticons' not in response['sets'][str(id)]:
        return None
    return response['sets'][str(id)]['emoticons']


class SpamDetector:
    def __init__(self):
        self.channels: List[ChannelMessages] = []

    async def init(self):
        global BANNED_WORDS
        global bttv_global

        BANNED_WORDS = await db.get_list_values_str(LIST_NAME_BANNED_WORDS)
        logger.info('Banned words: {}'.format(BANNED_WORDS))
        logger.info('Receiving bttv global emotes')
        bttv_global = await api.betterttv.get_global_emotes()

        channels = await db.getAutojoinChannels()
        for channel in channels:
            ch = await self.create_channel(channel['channel_name'])
            self.channels.append(ch)

        logger.debug('Starting topic listener')
        loop.create_task(db.redis.start_listener(self.redis_subscribe))
        logger.info('Init completed')

    async def create_channel(self, channel_name: str):
        ch = ChannelMessages(str(channel_name).lower())
        logger.info('Receiving emotes for channel {}'.format(ch.channel_name))
        ch.bttv_global = bttv_global
        ch.bttv_channel = await api.betterttv.get_channel_emotes(ch.channel_name)
        ch.fz_channel = parse_fz_emotes(await api.frankerfacez.get_channel_emotes(ch.channel_name))
        return ch

    async def redis_subscribe(self):
        logger.debug('redis_subscribe before')
        await db.redis.subscribe_event(redis_key.get_twitch_spam_detector_request_topic(), self.on_twitch_message)
        logger.debug('redis_subscribe after')

    async def on_twitch_message(self, body):
        logger.debug(body)

        if body['channel'].lower() in SKIP_LIST:
            return

        await self.push(body['channel'], body['sender'], body['message'], body['ts'], body['twitch_emotes'])

    async def run(self):
        while True:
            await asyncio.sleep(20)
            try:
                logger.debug('Checking...')
                for channel in self.channels:
                    if len(channel.messages) == 0 and len(channel.detections) == 0:
                        continue

                    logger.debug('Channel info {}: detections {}, messages {}'.format(channel.channel_name, len(channel.detections), len(channel.messages)))
                    for detection in channel.detections:
                        logger.info('Detection {} in {} last activity {}, triggered: {}, last ratio: {}'.format(detection, channel.channel_name, detection.last_activity, detection.triggered, detection.last_ratio))
                        for msg in detection.messages:
                            logger.info('From: {}, at {} Message: {} '.format(msg.sender, msg.received_ts, msg.original_message))

                    await channel.disabled_expired_triggers()
                    channel.detections = [x for x in channel.detections if not x.expired]
            except Exception as ex:
                logger.exception(ex)

    async def push(self, channel_name, sender, message, ts, twitch_emotes):
        channel: ChannelMessages = None
        for ch in self.channels:
            if ch.channel_name.lower() == channel_name.lower():
                channel = ch

        if channel is None:
            logger.info('Creating custom channel for {}'.format(channel_name))
            channel = await self.create_channel(channel_name)
            self.channels.append(channel)

        await channel.process(sender, message, ts, twitch_emotes)
        channel.clear_old_messages()


class ChannelMessage:
    def __init__(self, sender: str, text: str, ts: datetime):
        self.sender: str = sender
        self.original_message: str = unidecode(str(text))
        self.clear_message: str = self.clean(text)
        self.received_ts: datetime = ts
        self.detection: Detection = None

    def too_old(self)->bool:
        return self.received_ts + timedelta(seconds=INTERVAL_CHECK) < datetime.utcnow()

    @staticmethod
    def clean(text: str)->str:
        return ''.join(e for e in text.lower() if e.isalnum())

    @staticmethod
    def is_acceptable(text: str)->bool:
        # TODO: more rules
        if len(text.split(' ')) <= MIN_WORDS:
            return False

        if text.startswith('.') and 'Mass ban required by' in text:
            return False

        # try:
        #     number = int(ChannelMessage.clean(text))
        #     return False
        # except ValueError:
        #     pass

        return True


class Detection:
    def __init__(self):
        self.messages: List[ChannelMessage] = []
        self.last_activity: datetime = datetime.now()
        self.triggered: bool = False
        self.triggered_now: bool = False
        self.expired: bool = False
        self.last_ratio = 0

    async def add_message(self, message: ChannelMessage):
        self.last_activity: datetime = datetime.now()
        self.messages.append(message)
        self.check_triggers()

        if self.triggered:
            last_word = str(message.original_message.split(' ')[-1:][0])
            if last_word.startswith('@') and last_word not in BANNED_WORDS:
                logger.info('Appending {} to blacklist'.format(last_word))
                BANNED_WORDS.append(last_word)
                await db.add_to_list(LIST_NAME_BANNED_WORDS, last_word, None, None)
            else:
                logger.info('NOT appending {} to blacklist'.format(last_word))

    def too_old(self)->bool:
        if not self.triggered and self.last_activity + timedelta(seconds=INTERVAL_CHECK) < datetime.now():
            return True

        return False

    def is_trigger_expired(self)->bool:
        if self.triggered and self.last_activity + timedelta(seconds=INTERVAL_CHECK * 2) < datetime.now():
            self.expired = True
            return True

        return False

    def check_triggers(self):
        self.triggered_now = False
        if not self.triggered:
            self.messages = sorted(self.messages, key=lambda x: x.received_ts)

            partly = self.messages[-5:]
            max_ts = partly[-1].received_ts
            min_ts = partly[0].received_ts
            diff = (max_ts - min_ts).total_seconds()
            if diff == 0:
                diff = 0.01
            ratio = (len(partly) / diff)
            self.last_ratio = ratio
            if len(self.messages) >= 3 and ratio >= MPS_RATIO:
                self.triggered = True
                self.triggered_now = True


class ChannelMessages:
    def __init__(self, name):
        self.channel_name: str = name
        self.messages: List[ChannelMessage] = []
        self.detections: List[Detection] = []
        self.triggered: bool = False
        self.triggered_at: datetime = None
        self.bttv_global = None
        self.bttv_channel = None
        self.fz_channel = None
        self.spam_detected = False

    async def disabled_expired_triggers(self):
        has_expired = False
        for detection in self.detections:
            if (not detection.expired) and detection.is_trigger_expired():
                has_expired = True

        if has_expired:
            await self.action_disable_detection()

    def clear_old_messages(self):
        self.messages = [message for message in self.messages if not message.too_old()]
        self.detections = [detection for detection in self.detections if not detection.too_old()]
        #print('Total size: {}'.format(len(self.messages)))

    def get_result(self, first_text, second_text) -> float:
        try:
            return get_cosine_sim(first_text, second_text)[0][1]
        except ValueError:
            return 0

    async def find_detection(self, message: ChannelMessage)->[Detection, None]:
        for detection in self.detections:
            for active in detection.messages:
                if message.sender == active.sender:
                    continue

                result = self.get_result(message.original_message, active.original_message)
                if result < MATCH_THRESHOLD:
                    continue

                await detection.add_message(message)
                return detection

        for old_message in self.messages:
            if message.original_message in old_message.original_message:
                continue

            if message.original_message == old_message.original_message and message.sender != old_message.sender:
                result = 1.0
            else:
                result = self.get_result(message.original_message, old_message.original_message)
            if result < MATCH_THRESHOLD:
                continue

            return await self.update_detection(message, old_message)

        last_word = str(message.original_message.split(' ')[-1:][0])
        if last_word.startswith('@') and last_word in BANNED_WORDS:
            logger.info('Banning user {} for banned word {} in message: {}'.format(message.sender, last_word, message.original_message))
            await self.action_ban([{'sender': message.sender, 'message': message.original_message, 'ts': message.received_ts}])
            return None

        return None

    def clear_emotes(self, text: str, twitch_emotes=None)->str:
        #  58765:0-10,12-22,24-34,36-46,48-58,60-70
        # 81249:0-11,13-24,26-37,39-50,52-63,65-76,78-89
        if twitch_emotes:
            if isinstance(twitch_emotes, datetime):
                logger.error('Somehow received datetime into twitch_emotes: {}'.format(twitch_emotes))
            else:
                emote_list = twitch_emotes.split('/')
                tmp_list = []
                for emote in emote_list:
                    if ':' not in emote:
                        continue

                    parts = emote.split(':')
                    if len(parts) < 1 or '-' not in parts[1]:
                        continue

                    intervals = parts[1].split(',')
                    for interval in intervals:
                        cut_values = interval.split('-')
                        tmp_list.append(text[int(cut_values[0]):(int(cut_values[1]) + 1)])

                if tmp_list:
                    for emote in tmp_list:
                        text = str(text).replace(' ' + emote, '')

        if self.bttv_global is not None:
            for emote in self.bttv_global:
                text = str(text).replace(' ' + emote['code'], '')

        if self.bttv_channel is not None and 'emotes' in self.bttv_channel:
            for emote in self.bttv_channel['emotes']:
                text = str(text).replace(' ' + emote['code'], '')

        if self.fz_channel is not None:
            for emote in self.fz_channel:
                text = str(text).replace(' ' + emote['name'], '')

        return " ".join(text.strip().split())

    async def process(self, sender: str, message: str, ts: datetime = None, twitch_emotes: str = None):
        message = self.clear_emotes(message, twitch_emotes)
        if not ChannelMessage.is_acceptable(message):
            return

        logger.debug('Message after clear_emotes: {}'.format(message))
        msg = ChannelMessage(sender, message, ts=ts)
        detection = await self.find_detection(msg)
        if detection is None:
            self.messages.append(msg)
        elif detection.triggered_now:
            logger.info('New detection triggered in channel {}. Message: {}'.format(self.channel_name, msg.original_message))
            await self.action_enable_detection()

            users = []
            for detected_message in detection.messages:
                if detected_message.sender not in users:
                    users.append({'sender': detected_message.sender, 'message': detected_message.original_message, 'ts': detected_message.received_ts})

            if users:
                await self.action_ban(users)
        elif detection.triggered:
            await self.action_enable_detection()
            logger.info('Additionam message for existing detection in channel {}. Message: {}'.format(self.channel_name, msg.original_message))
            await self.action_ban([{'sender': msg.sender, 'message': msg.original_message, 'ts': msg.received_ts}])

    async def update_detection(self, new_message: ChannelMessage, prev_message: ChannelMessage)->Detection:
        detection = Detection()
        await detection.add_message(new_message)
        await detection.add_message(prev_message)
        self.detections.append(detection)
        return detection

    async def send_response(self, body):
        await db.redis.publish_event(redis_key.get_twitch_spam_detector_response_topic(), body)

    async def action_ban(self, users: List[Dict]):
        body = {
            "action": "ban",
            "users": users,
            "channel": self.channel_name
        }

        await self.send_response(body)

        for user in users:
            await db.saveSpamLog(self.channel_name, user['sender'], user['message'], user['ts'])

    async def action_enable_detection(self):
        if self.spam_detected:
            return

        self.spam_detected = True

        body = {
            "action": "detection",
            "status": 1,
            "channel": self.channel_name
        }
        logger.info('Enabling detection in channel {}'.format(self.channel_name))
        await self.send_response(body)

    async def action_disable_detection(self):
        if not self.spam_detected:
            return

        self.spam_detected = False

        body = {
            "action": "detection",
            "status": 0,
            "channel": self.channel_name
        }
        logger.info('Disabling detection in channel {}'.format(self.channel_name))
        await self.send_response(body)

    async def action_message(self, message):
        body = {
            "action": "message",
            "text": message,
            "channel": self.channel_name
        }

        await self.send_response(body)