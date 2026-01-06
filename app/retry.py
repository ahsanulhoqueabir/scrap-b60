"""
Retry logic and decorators for handling transient failures
"""
import time
import functools
from typing import Callable, Any, Tuple, Type
from app.config import config
from app.logger import setup_logger

logger = setup_logger(__name__)


def retry_on_exception(
    max_retries: int = None,
    delay: int = None,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    backoff: bool = True
) -> Callable:
    """
    Decorator to retry a function on exception
    
    Args:
        max_retries: Maximum number of retry attempts (default: from config)
        delay: Initial delay between retries in seconds (default: from config)
        exceptions: Tuple of exceptions to catch and retry on
        backoff: Whether to use exponential backoff (doubles delay each retry)
        
    Returns:
        Decorated function with retry logic
        
    Example:
        @retry_on_exception(max_retries=3, delay=2)
        def fetch_data():
            response = requests.get(url)
            return response.json()
    """
    if max_retries is None:
        max_retries = config.MAX_RETRIES
    if delay is None:
        delay = config.RETRY_DELAY
        
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    result = func(*args, **kwargs)
                    if attempt > 0:
                        logger.info(f"{func.__name__} succeeded on attempt {attempt + 1}")
                    return result
                    
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_retries:
                        logger.warning(
                            f"{func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}): {str(e)}. "
                            f"Retrying in {current_delay} seconds..."
                        )
                        time.sleep(current_delay)
                        
                        # Exponential backoff
                        if backoff:
                            current_delay *= 2
                    else:
                        logger.error(
                            f"{func.__name__} failed after {max_retries + 1} attempts: {str(e)}"
                        )
            
            # If all retries failed, raise the last exception
            raise last_exception
            
        return wrapper
    return decorator


def retry_with_callback(
    on_failure: Callable = None,
    max_retries: int = None,
    delay: int = None
) -> Callable:
    """
    Decorator to retry with a callback function on final failure
    
    Args:
        on_failure: Callback function to execute if all retries fail
        max_retries: Maximum number of retry attempts
        delay: Delay between retries in seconds
        
    Returns:
        Decorated function with retry logic and failure callback
    """
    if max_retries is None:
        max_retries = config.MAX_RETRIES
    if delay is None:
        delay = config.RETRY_DELAY
        
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt < max_retries:
                        logger.warning(
                            f"{func.__name__} failed (attempt {attempt + 1}): {str(e)}. "
                            f"Retrying in {delay} seconds..."
                        )
                        time.sleep(delay)
                    else:
                        logger.error(f"{func.__name__} failed after {max_retries + 1} attempts")
                        if on_failure:
                            on_failure(e, *args, **kwargs)
                        raise
        return wrapper
    return decorator
