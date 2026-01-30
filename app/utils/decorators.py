"""
Custom decorators for the application.
Includes the @measure_time decorator for endpoint performance monitoring.
"""

import time
import functools
from typing import Callable, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def measure_time(func: Callable) -> Callable:
    """
    Decorator that measures and logs the execution time of a function.
    
    This decorator can be applied to both synchronous and asynchronous functions.
    It logs the function name and execution time in milliseconds.
    
    Usage:
        @measure_time
        async def my_endpoint():
            ...
    
    Args:
        func: The function to be measured
        
    Returns:
        Wrapped function with timing measurement
    
    Example output:
        INFO: [TIMING] get_items executed in 15.23ms
    """
    
    @functools.wraps(func)
    async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
        start_time = time.perf_counter()
        try:
            result = await func(*args, **kwargs)
            return result
        finally:
            end_time = time.perf_counter()
            execution_time_ms = (end_time - start_time) * 1000
            logger.info(
                f"[TIMING] {func.__name__} executed in {execution_time_ms:.2f}ms"
            )
    
    @functools.wraps(func)
    def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
        start_time = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            end_time = time.perf_counter()
            execution_time_ms = (end_time - start_time) * 1000
            logger.info(
                f"[TIMING] {func.__name__} executed in {execution_time_ms:.2f}ms"
            )
    
    # Return appropriate wrapper based on function type
    import asyncio
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper


def log_exceptions(func: Callable) -> Callable:
    """
    Decorator that logs exceptions before re-raising them.
    
    Useful for debugging and monitoring application errors.
    
    Args:
        func: The function to be wrapped
        
    Returns:
        Wrapped function with exception logging
    """
    
    @functools.wraps(func)
    async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.exception(f"Exception in {func.__name__}: {str(e)}")
            raise
    
    @functools.wraps(func)
    def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.exception(f"Exception in {func.__name__}: {str(e)}")
            raise
    
    import asyncio
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper
