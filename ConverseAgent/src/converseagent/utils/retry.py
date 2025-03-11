import logging
import random
import time
from functools import wraps
from typing import Any, Callable, Tuple, Type, TypeVar, Union

logger = logging.getLogger(__name__)
T = TypeVar("T")  # Type variable for return type


def with_exponential_backoff(
    retryable_exceptions: Union[
        Type[Exception], Tuple[Type[Exception], ...]
    ] = Exception,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    jitter_factor: float = 0.1,
) -> Callable:
    """
    Decorator that implements exponential backoff retry logic.

    Args:
        retryable_exceptions: Exception or tuple of exceptions to retry on
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        jitter_factor: Randomization factor for jitter (0.1 = 10% jitter)

    Returns:
        Callable: Decorated function with retry logic

    Example:
        @with_exponential_backoff(
            retryable_exceptions=(ConnectionError, TimeoutError),
            max_retries=3,
            base_delay=1.0
        )
        def my_function():
            # Your code here
            pass
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception = None

            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e

                    if attempt == max_retries - 1:
                        logger.error(
                            f"All retry attempts failed for {func.__name__}. "
                            f"Final error: {str(e)}"
                        )
                        raise last_exception

                    # Calculate delay with exponential backoff
                    delay = min(max_delay, base_delay * (2**attempt))

                    # Add jitter to prevent thundering herd
                    jitter = random.uniform(0, jitter_factor * delay)
                    total_delay = delay + jitter

                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries} failed for {func.__name__}. "
                        f"Retrying in {total_delay:.2f} seconds. Error: {str(e)}"
                    )
                    time.sleep(total_delay)

            # This line should never be reached due to the raise in the loop,
            # but adding it for type safety
            raise (
                last_exception
                if last_exception
                else RuntimeError("Unexpected retry failure")
            )

        return wrapper

    return decorator
