import time
from functools import wraps

def rate_limit(seconds=5):
    """Decorator to enforce minimum delay between calls."""
    def decorator(func):
        last_call = [0.0]

        @wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_call[0]
            if elapsed < seconds:
                time.sleep(seconds - elapsed)
            last_call[0] = time.time()
            return func(*args, **kwargs)

        return wrapper
    return decorator
