import logging

from object.Base import Base


class GlobalEventProcessor(Base):
    instance = None

    def __init__(self):
        self.event_name: str = None

    @classmethod
    def get_instance(cls):
        if cls.instance is None:
            cls.instance = cls()

        return cls.instance

    async def process(self, **args):
        raise NotImplemented

    def get_logger(self)->logging:
        return logging.getLogger('krya.tg')
