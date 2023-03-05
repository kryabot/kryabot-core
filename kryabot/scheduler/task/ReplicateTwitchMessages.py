from models.dao.BotTask import BotTask
from scheduler.Task import Task
from scrape.twitch_message_history import replicate_messages


class ReplicateTwitchMessages(Task):

    async def process(self, task: BotTask):
        async def _update_cursor(current_cursor):
            task.patchRequest({'cursor': current_cursor})
            await task.save()

        cursor = task.request['cursor'] if 'cursor' in task.request else None
        count = await replicate_messages(task.request['channel_name'], task.request['user_id'], cursor, _update_cursor)
        task.patchResponse({'count': count})
