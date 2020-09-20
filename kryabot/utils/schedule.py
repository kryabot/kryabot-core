import asyncio


def schedule_task_periodically(wait_time, func, logger=None, reporter=None, *args):
    """
    Schedule a function to run periodically as an asyncio.Task
    :param wait_time: interval (in seconds)
    :param func: the function that will be run
    :param reporter: reporter object
    :param logger: logger object
    :param args: any args needed to be provided to func
    :return: an asyncio Task that has been scheduled to run
    """

    async def run_periodically(wait_time, func, logger=None, reporter=None, *args):
        """
        Helper for schedule_task_periodically.
        Wraps a function in a coroutine that will run the
        given function indefinitely
        :param wait_time: seconds to wait between iterations of func
        :param func: the function that will be run
        :param reporter: exception will be reported there if provided
        :param logger: exception will be logger here if provided
        :param args: any args that need to be provided to func
        """
        while True:
            try:
                if logger:
                    logger.debug("Periodic run of function: {}".format(func))

                await func(*args)
            except Exception as ex:
                if logger:
                    logger.exception(ex)

                if reporter:
                    await reporter(ex, func, *args)

            await asyncio.sleep(wait_time)

    return asyncio.create_task(run_periodically(wait_time=wait_time, func=func, logger=logger, reporter=reporter, *args))


async def cancel_scheduled_task(task):
    """
    Gracefully cancels a task
    :type task: asyncio.Task
    """
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass