import functools


def exception(logger=None, raise_error=True, reporter=None):
    """
    A decorator that wraps the passed in function.
    On exception, logs and sends to monitoring chat
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            internal_logger = logger() if callable(logger) else logger

            try:
                return await func(*args, **kwargs)
            except Exception as err:
                if internal_logger:
                    internal_logger.exception(err)

                if reporter and callable(reporter):
                    try:
                        await reporter(err, func.__name__)
                    except Exception as reporter_exception:
                        internal_logger.exception(reporter_exception)
                else:
                    internal_logger.info("Got exception but reporter is not defined")

                # re-raise the exception
                if raise_error:
                    raise err
        return wrapper
    return decorator


def log_exception_ignore(log=None, reporter=None):
    return exception(logger=log, raise_error=False, reporter=reporter)


def log_exception(log=None, reporter=None):
    return exception(logger=log, raise_error=True, reporter=reporter)



