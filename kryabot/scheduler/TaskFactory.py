from models.dao.BotTask import TaskType
from scheduler.task.Demo import Demo
from scheduler.task.ReplicateTwitchMessages import ReplicateTwitchMessages


def get_task_executor(task_type: TaskType):
    return {
        TaskType.DEMO: Demo,
        TaskType.FETCH_TWITCH_MESSAGES: ReplicateTwitchMessages,
    }.get(task_type, None)
