from logging import Logger
from typing import Dict
from datetime import datetime, timedelta
from random import randint


class Command:
    def __init__(self, raw: Dict, updated_at: datetime, logger: Logger):
        self.raw: Dict = None
        self.logger: Logger = logger
        self.channel_id: int = None
        self.command_id: int = None
        self.command_name: str = None
        self.action: str = None
        self.level: int = None
        self.active: bool = None
        self.use_cooldown: int = None
        self.trigger_cooldown: int = None
        self.message: str = None
        self.additional_text: str = None
        self.usages: int = None
        self.check_type: int = None

        self.last_trigger: datetime = None
        self.last_use: datetime = None
        self.options: [] = None
        self.last_update: datetime = None
        self.set(raw, updated_at)

    def set(self, raw: Dict, updated_at: datetime):
        self.raw = raw
        self.last_update = updated_at
        self.channel_id = int(raw['channel_id'])
        self.command_id = int(raw['channel_command_id'])
        self.command_name = str(raw['command'])
        self.action = str(raw['action'])
        self.level = int(raw['level']) or 0
        self.active = bool(int(raw['active']))
        self.use_cooldown = int(raw['cooldown']) or 30
        self.trigger_cooldown = int(raw['repeat_amount']) or 0
        self.message = str(raw['reply_message'] or '')
        self.additional_text = str(raw['additional_text'] or '')
        self.usages = int(raw['used']) or 0
        self.options = raw['options']
        self.check_type = int(raw['check_type']) or 0

    def used(self)->None:
        self.last_use = datetime.now()
        self.usages = self.usages + 1

    def triggered(self)->None:
        self.used()
        self.last_trigger = datetime.now()

    def can_access(self, lvl: int)->bool:
        return lvl >= self.level

    def can_use(self)->bool:
        if self.last_use is None:
            return True

        return datetime.now() > self.last_use + timedelta(seconds=self.use_cooldown)

    def can_trigger(self)->bool:
        self.logger.debug('Channel ID {} command {}: cooldown = {}, can use: {}, last trigger at {} '.format(self.channel_id, self.command_name, self.trigger_cooldown, self.can_use(), self.last_trigger))
        if self.trigger_cooldown <= 0:
            return False

        if not self.can_use():
            return False

        if self.last_trigger is None:
            return True

        return datetime.now() > self.last_trigger + timedelta(seconds=self.trigger_cooldown)

    def outdated(self, ts: datetime)->bool:
        return self.last_update < ts

    def get_response(self)->str:
        if self.options is None or len(self.options) == 0:
            return self.message
        if len(self.options) == 1:
            return self.options[0]['response']

        possibilities = []
        for option in self.options:
            if option['ratio'] < 1:
                continue

            ratio = min(option['ratio'], 100)
            for i in range(0, ratio):
                possibilities.append(option['response'])

        if len(possibilities) == 0:
            return self.options[0]['response']

        roll = randint(0, len(possibilities) - 1)
        return possibilities[roll]

