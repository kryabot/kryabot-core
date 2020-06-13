import functools
import traceback


def exception(logger=None, raise_error=True, reporter=None, monitoring_id=1255287898):
    """
    A decorator that wraps the passed in function.
    On exception, logs and sends to monitoring chat
    """
    def decorator(function):
        @functools.wraps(function)
        async def wrapper(*args, **kwargs):
            try:
                return await function(*args, **kwargs)
            except Exception as err:
                tb = ''.join(traceback.format_tb(err.__traceback__))
                if logger is not None:
                    logger.exception(err)

                if reporter is not None:
                    try:
                        await reporter(str(err), tb)
                    except:
                        pass

                # re-raise the exception
                if raise_error:
                    raise
        return wrapper
    return decorator


def log_exception_ignore(log=None, reporter=None):
    return exception(logger=log, raise_error=False, reporter=reporter)


def log_exception(log=None, reporter=None):
    return exception(logger=log, raise_error=True, reporter=reporter)



