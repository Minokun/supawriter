# -*- coding: utf-8 -*-
"""
Lightweight async retry utility for transient failures.

Usage:
    @async_retry(max_retries=3, backoff_base=1.0, retryable=(ConnectionError, TimeoutError))
    async def flaky_operation():
        ...

    result = await retry_async(flaky_func, args, max_retries=3)
"""

import asyncio
import logging
import functools
from typing import Tuple, Type, Optional, Callable, Any

logger = logging.getLogger(__name__)

# Common transient exceptions worth retrying
TRANSIENT_DB_ERRORS: Tuple[Type[Exception], ...] = (
    ConnectionError,
    TimeoutError,
    OSError,
)

TRANSIENT_NETWORK_ERRORS: Tuple[Type[Exception], ...] = (
    ConnectionError,
    TimeoutError,
    OSError,
)

# Try to include SQLAlchemy and httpx transient errors if available
try:
    from sqlalchemy.exc import OperationalError, DisconnectionError, InterfaceError
    TRANSIENT_DB_ERRORS = TRANSIENT_DB_ERRORS + (OperationalError, DisconnectionError, InterfaceError)
except ImportError:
    pass

try:
    import httpx
    TRANSIENT_NETWORK_ERRORS = TRANSIENT_NETWORK_ERRORS + (httpx.ConnectError, httpx.ReadTimeout)
except ImportError:
    pass


def async_retry(
    max_retries: int = 3,
    backoff_base: float = 1.0,
    backoff_max: float = 30.0,
    retryable: Tuple[Type[Exception], ...] = TRANSIENT_DB_ERRORS,
    on_retry: Optional[Callable] = None,
):
    """
    Decorator for async functions that should be retried on transient failures.

    Args:
        max_retries: Maximum number of retry attempts (0 = no retries)
        backoff_base: Base delay in seconds (exponential: base * 2^attempt)
        backoff_max: Maximum delay cap in seconds
        retryable: Tuple of exception types that trigger a retry
        on_retry: Optional callback(attempt, exception) called before each retry
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except retryable as e:
                    last_exception = e
                    if attempt < max_retries:
                        delay = min(backoff_base * (2 ** attempt), backoff_max)
                        logger.warning(
                            f"[retry] {func.__name__} attempt {attempt + 1}/{max_retries + 1} "
                            f"failed: {type(e).__name__}: {e}. Retrying in {delay:.1f}s..."
                        )
                        if on_retry:
                            on_retry(attempt + 1, e)
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"[retry] {func.__name__} failed after {max_retries + 1} attempts: "
                            f"{type(e).__name__}: {e}"
                        )
            raise last_exception
        return wrapper
    return decorator


async def retry_async(
    func: Callable,
    *args,
    max_retries: int = 3,
    backoff_base: float = 1.0,
    backoff_max: float = 30.0,
    retryable: Tuple[Type[Exception], ...] = TRANSIENT_DB_ERRORS,
    **kwargs,
) -> Any:
    """
    Functional retry: call an async function with retry logic.

    Args:
        func: Async callable to execute
        *args: Positional arguments for func
        max_retries: Maximum retry attempts
        backoff_base: Base delay in seconds
        backoff_max: Maximum delay cap
        retryable: Exception types that trigger retry
        **kwargs: Keyword arguments for func

    Returns:
        Result of func(*args, **kwargs)
    """
    last_exception = None
    for attempt in range(max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except retryable as e:
            last_exception = e
            if attempt < max_retries:
                delay = min(backoff_base * (2 ** attempt), backoff_max)
                logger.warning(
                    f"[retry] {func.__name__} attempt {attempt + 1}/{max_retries + 1} "
                    f"failed: {type(e).__name__}: {e}. Retrying in {delay:.1f}s..."
                )
                await asyncio.sleep(delay)
            else:
                logger.error(
                    f"[retry] {func.__name__} failed after {max_retries + 1} attempts: "
                    f"{type(e).__name__}: {e}"
                )
    raise last_exception
