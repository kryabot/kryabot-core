from models.dao.BotTask import BotTask
from scheduler.Task import Task


class Demo(Task):
    async def process(self, task: BotTask):
        print(task.request['row'])
        task.patchRequest({"internal": "demo"})
        self.logger.info('Running demo task: {}'.format(task))
        raise ValueError('demo exception')
