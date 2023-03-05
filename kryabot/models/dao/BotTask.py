import datetime

from sqlalchemy import Column, func, select
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import DateTime, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base
from utils.DaoUtils import DaoUtils
import enum

Base = declarative_base()


class TaskType(enum.Enum):
    DEMO = "DEMO"
    FETCH_TWITCH_MESSAGES = "FETCH_TWITCH_MESSAGES"


class TaskStatus(enum.Enum):
    NEW = "NEW"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    DELAYED = "DELAYED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class BotTask(Base, DaoUtils):
    __tablename__ = "bot_task"

    id = Column("bot_task_id", Integer, primary_key=True)
    task_type = Column(String, nullable=False)
    task_status = Column(String, nullable=False)
    started_at = Column(DateTime, nullable=False)
    finished_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    retries = Column(Integer, default=0)
    request = Column(JSONB)
    response = Column(JSONB)

    def __repr__(self):
        return f"BotTask(bot_task_id={self.id!r}, task_type={self.task_type!r}, task_status={self.task_status!r}, started_at={self.started_at!r} finished_at={self.finished_at!r}, created_at={self.created_at!r}, retries={self.retries!r})"

    async def updateStatus(self, status: TaskStatus):
        self.task_status = status.value

        if status == TaskStatus.PROCESSING:
            self.started_at = datetime.datetime.utcnow()

        if status == TaskStatus.COMPLETED or status == TaskStatus.FAILED:
            self.finished_at = datetime.datetime.utcnow()

        return await self.save()

    async def markStarted(self):
        return await self.updateStatus(TaskStatus.PROCESSING)

    async def markCompleted(self):
        return await self.updateStatus(TaskStatus.COMPLETED)

    async def markFailed(self, exception: Exception = None):
        if exception:
            self.patchResponse({'error': repr(exception)})
        return await self.updateStatus(TaskStatus.FAILED)

    def _patch_json(self, update, field):
        if field:
            patched = dict(field)
            patched.update(update)
        else:
            patched = update
        return patched

    def patchResponse(self, update):
        self.response = self._patch_json(update, self.response)

    def patchRequest(self, update):
        self.request = self._patch_json(update, self.request)

    async def markCancelled(self):
        return await self.updateStatus(TaskStatus.CANCELLED)

    @staticmethod
    async def getNextNewTask():
        query = select(BotTask).where(BotTask.task_status == TaskStatus.NEW.value).order_by(BotTask.created_at.asc()).limit(1)
        response = await DaoUtils.execute_first(query)

        return response[0] if response else None

    @staticmethod
    def createTask(task_type: TaskType, request):
        return BotTask(task_type=task_type.value, task_status=TaskStatus.NEW.value, request=request)

