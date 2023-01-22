from logging import Logger

from object.ApiHelper import ApiHelper
from object.BotConfig import BotConfig
from object.Database import Database
from twbot import ResponseAction
from twitchio.websocket import WebsocketConnection


class Processor:
    cfg: BotConfig = None
    instance = None

    def __init__(self):
        if Processor.cfg is None:
            Processor.cfg = BotConfig.get_instance()

        self.silent: bool = False
        self.db: Database = None
        self.api: ApiHelper = None
        self.logger: Logger = None
        self.cfg: BotConfig = Processor.cfg
        self.ready: bool = False

    async def update(self, channel_id: int = None)->None:
        raise Exception('Update method must be implemented')

    def set_tools(self, logger: Logger, db: Database, api: ApiHelper)->None:
        self.logger = logger
        self.db = db
        self.api = api

    async def process(self, *args):
        raise Exception('Process method must be implemented')

    def get_int(self, val)-> int:
        try:
            return int(val)
        except:
            return 0

    def init_struct(self, list, channel_id: int = None):
        if channel_id is None:
            list = {}
        else:
            list[channel_id] = []

        return list

    def add_data(self, list, array):
        for row in array:
            id = int(row['channel_id'])
            if id not in list:
                list[id] = []

            list[id].append(row)

        return list

    @classmethod
    def get_instance(cls):
        if cls.instance:
            return cls.instance

        return cls()
