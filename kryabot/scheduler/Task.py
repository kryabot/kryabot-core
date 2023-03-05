import logging

from object.Base import Base


class Task(Base):
    def __init__(self):
        self.logger = logging.getLogger('krya.scheduler')

    async def process(self, task):
        raise NotImplementedError('process() method is not implemented!')
