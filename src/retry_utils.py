import time
import functools
from typing import Callable, Tuple, Type

from logging_config import setup_logging

logger = setup_logging()


def retry_with_backoff(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    exponential_base: int = 2,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
):
    """Retry decorator with exponential backoff.

    Wraps a function so that if it raises one of the specified exceptions,
    it will be retried automatically with increasing delays between attempts.

    Delay pattern (with defaults): 1s → 2s → give up
    e.g. base_delay=1, exponential_base=2: attempt 1 fails → wait 1s,
                                            attempt 2 fails → wait 2s,
                                            attempt 3 fails → raise.

    Args:
        max_attempts:    Max number of tries before re-raising (default 3)
        base_delay:      Seconds to wait before the first retry (default 1.0)
        exponential_base: Each retry multiplies the previous delay by this (default 2)
        exceptions:      Only retry on these exception types (default: all exceptions)

    Usage:
        @retry_with_backoff(max_attempts=3, exceptions=(SpotifyException,))
        def fetch_from_spotify():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)  # Preserve the original function's name/docstring
        def wrapper(*args, **kwargs):
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)

                except exceptions as e:
                    # If we've used all attempts, re-raise so the caller sees the error
                    if attempt == max_attempts:
                        logger.error(
                            '%s failed after %d attempts: %s',
                            func.__name__, max_attempts, e,
                        )
                        raise

                    # Otherwise wait and try again — delay doubles each round
                    delay = base_delay * (exponential_base ** (attempt - 1))
                    logger.warning(
                        '%s attempt %d/%d failed: %s. Retrying in %.1fs...',
                        func.__name__, attempt, max_attempts, e, delay,
                    )
                    time.sleep(delay)

        return wrapper
    return decorator
