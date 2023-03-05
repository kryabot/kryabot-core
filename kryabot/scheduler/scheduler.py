import asyncio
import logging

from models.dao.BotTask import BotTask, TaskType
from object.Base import Base
from scheduler.TaskFactory import get_task_executor


class Scheduler(Base):
    def __init__(self):
        self.logger = logging.getLogger('krya.scheduler')

    async def run(self):
        while True:
            try:
                task: BotTask = await BotTask.getNextNewTask()
                if not task:
                    await asyncio.sleep(3)
                    continue

                await self.process_task(task)
            except Exception as ex:
                self.logger.exception(ex)

    async def process_task(self, task: BotTask):
        if task.response is None:
            task.response = {}

        task_type = TaskType(task.task_type)

        executor = get_task_executor(task_type)
        if not executor:
            await task.markFailed(exception=Exception("Failed to find executor for task type {}".format(task_type.value)))
            return

        await task.markStarted()
        self.logger.info("Scheduled task {} started".format(task.id))
        try:
            await executor().process(task)
            await task.markCompleted()
            self.logger.info("Scheduled task {} completed".format(task.id))
        except Exception as err:
            self.logger.info(task)
            self.logger.exception(err)
            self.logger.info("Scheduled task {} failed".format(task.id))
            await task.markFailed(exception=err)
