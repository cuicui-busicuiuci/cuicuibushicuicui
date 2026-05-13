import logging
import time
from functools import wraps


class BaseSource:
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def _retry(self, fn, max_retries: int = 3, delay: float = 1.0):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries):
                try:
                    return fn(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if attempt < max_retries - 1:
                        wait = delay * (2 ** attempt)
                        self.logger.warning(f"重试 {attempt+1}/{max_retries}: {e}, 等待 {wait}s")
                        time.sleep(wait)
            raise last_error
        return wrapper

    def _handle_error(self, e: Exception, context: str):
        self.logger.error(f"{context}: {e}")
        return None
