import functools
import asyncio


def run_in_executor(f, l=None):
    @functools.wraps(f)
    def inner(*args, **kwargs):
        loop = l or asyncio.get_event_loop()
        return loop.run_in_executor(None, lambda: f(*args, **kwargs))

    return inner

def run_in_executor_2(f):
    @functools.wraps(f)
    def inner(*args, **kwargs):
        loop = asyncio.get_event_loop()
        return loop.run_in_executor(None, functools.partial(f, *args, **kwargs))

    return inner