"""Utility functions for the USA Cycling Results Parser package."""

import contextlib
import functools
import hashlib
import json
import logging
import os
import pickle
import sys
import tempfile
import threading
import time
from collections.abc import Callable
from datetime import datetime
from typing import Any, TypeVar, cast

# Configure base logger
logger = logging.getLogger("usac_velodata")

# Default log format for the library
DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Mapping for log level strings to logging constants
LOG_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}

# Type variable for generic function typing
T = TypeVar("T")

# Cache directory setup
DEFAULT_CACHE_DIR = os.path.join(tempfile.gettempdir(), "usac_velodata_cache")


class CacheError(Exception):
    """Exception raised for cache-related errors."""

    pass


def configure_logging(
    level: int | str = logging.INFO,
    log_file: str | None = None,
    log_format: str | None = None,
    date_format: str | None = None,
    propagate: bool = False,
    add_console_handler: bool = True,
    console_level: int | str | None = None,
    file_mode: str = "a",
    file_encoding: str = "utf-8",
) -> None:
    """Configure the package's logging system with extensive customization.

    This function sets up the logger for the usac_velodata package with options
    for console output, file output, format customization, and log level settings.

    Args:
        level: Logging level as int or string ('debug', 'info', 'warning', etc)
        log_file: Optional path to log file for file-based logging
        log_format: Custom log format string (default: timestamp - name - level)
        date_format: Custom date format for log timestamps
        propagate: Whether to propagate logs to parent loggers
        add_console_handler: Whether to add a console handler
        console_level: Separate log level for console handler
        file_mode: File open mode ('a' for append, 'w' for overwrite)
        file_encoding: Encoding for log file

    Examples:
        # Basic configuration with INFO level to console
        configure_logging()

        # Debug level to both console and file
        configure_logging(level='debug', log_file='usac_velodata.log')

        # Different levels for console and file
        configure_logging(level='error', log_file='errors.log',
                         add_console_handler=True, console_level='info')

    """
    # Convert string level to int if needed
    if isinstance(level, str):
        level = LOG_LEVELS.get(level.lower(), logging.INFO)

    if console_level is not None and isinstance(console_level, str):
        console_level = LOG_LEVELS.get(console_level.lower(), logging.INFO)
    elif console_level is None:
        console_level = level

    # Set format strings
    log_format = log_format or DEFAULT_LOG_FORMAT
    date_format = date_format or DEFAULT_DATE_FORMAT
    formatter = logging.Formatter(log_format, date_format)

    # Remove any existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Add file handler if requested
    if log_file:
        # Ensure directory exists
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

        file_handler = logging.FileHandler(log_file, mode=file_mode, encoding=file_encoding)
        file_handler.setFormatter(formatter)
        file_handler.setLevel(level)
        logger.addHandler(file_handler)

    # Add console handler if requested
    if add_console_handler:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(console_level)
        logger.addHandler(console_handler)

    # Configure the logger itself
    min_level = min(level, console_level) if add_console_handler else level
    logger.setLevel(min_level)
    logger.propagate = propagate


def get_logger(name: str | None = None) -> logging.Logger:
    """Get a logger instance for a specific module or component.

    Creates a child logger of the main usac_velodata logger with the specified name.
    This allows for component-specific logging control.

    Args:
        name: Name of the component/module for the logger

    Returns:
        Logger instance for the specified component

    Examples:
        # Get logger for parser component
        parser_logger = get_logger('parser')
        parser_logger.debug('Parsing started')

    """
    if name:
        return logger.getChild(name)
    return logger


def enable_debug_logging(log_file: str | None = None) -> None:
    """Quick utility to enable debug level logging.

    Args:
        log_file: Optional log file path

    """
    configure_logging(level=logging.DEBUG, log_file=log_file)


def disable_logging() -> None:
    """Disable all logging output from the package."""
    logger.setLevel(logging.CRITICAL + 1)
    logger.handlers = []
    logger.propagate = False


def log_function_call(func):
    """Log function calls with parameters and return values.

    Args:
        func: The function to wrap with logging

    Returns:
        Wrapped function with logging

    Examples:
        @log_function_call
        def fetch_results(race_id):
            # function implementation
            return results

    """

    def wrapper(*args, **kwargs):
        func_logger = get_logger(func.__module__)
        # Use simpler function name without qualification for better test compatibility
        func_name = func.__name__

        # Log function call with arguments
        arg_str = ", ".join([repr(a) for a in args])
        kwarg_str = ", ".join([f"{k}={v!r}" for k, v in kwargs.items()])
        params = f"{arg_str}{', ' if arg_str and kwarg_str else ''}{kwarg_str}"

        func_logger.debug(f"Calling {func_name}({params})")

        try:
            result = func(*args, **kwargs)
            func_logger.debug(f"{func_name} returned successfully")
            return result
        except Exception as e:
            func_logger.exception(f"{func_name} raised {type(e).__name__}: {e!s}")
            raise

    return wrapper


def log_to_json(message: str, level: int | str = logging.INFO, **extra_fields) -> None:
    """Log a message in JSON format with additional fields.

    Useful for structured logging that can be consumed by log processors.

    Args:
        message: Log message
        level: Log level
        **extra_fields: Additional fields to include in the JSON log

    Examples:
        log_to_json("Race data fetched",
                   race_id="2020-123",
                   fetch_time=0.123,
                   items_count=15)

    """
    # Convert string level to int if needed
    if isinstance(level, str):
        level = LOG_LEVELS.get(level.lower(), logging.INFO)

    # Create JSON log entry
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "message": message,
        "level": logging.getLevelName(level),
        **extra_fields,
    }

    # Log the JSON entry
    logger.log(level, json.dumps(log_entry))


class LogContext:
    """Context manager for grouping related log messages with context information.

    Examples:
        with LogContext("Fetching race results", race_id="2020-123"):
            # Code and logging within this context will include the context info
            logger.info("Starting HTTP request")
            # ...
            logger.info("Processing response")

    """

    def __init__(self, context_name: str, logger_name: str | None = None, **context_data):
        """Initialize logging context.

        Args:
            context_name: Name for this logging context
            logger_name: Optional specific logger name
            **context_data: Additional context data to include in logs

        """
        self.context_name = context_name
        self.context_data = context_data
        self.logger = get_logger(logger_name) if logger_name else logger
        self.old_factory = logging.getLogRecordFactory()

    def __enter__(self):
        """Set up context by adding contextual information to log records."""

        # Create a custom record factory that adds our context
        def record_factory(*args, **kwargs):
            record = self.old_factory(*args, **kwargs)
            record.context_name = self.context_name
            # Don't set context_data directly on record to avoid conflicts
            # with extra parameter in log methods
            return record

        # Set our custom factory
        logging.setLogRecordFactory(record_factory)
        # Use extra parameter instead of modifying LogRecord directly
        self.logger.info(f"Entered context: {self.context_name}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Restore original logging when exiting the context."""
        if exc_type:
            self.logger.error(f"Error in context {self.context_name}: {exc_val}")
        else:
            self.logger.info(f"Exited context: {self.context_name}")

        # Restore original record factory
        logging.setLogRecordFactory(self.old_factory)
        return False  # Don't suppress exceptions


def rate_limit_decorator(
    max_calls: int, period: float, backoff_factor: float = 2.0, max_backoff: float = 60.0, jitter: bool = True
) -> callable:
    """Rate limit function calls with exponential backoff.

    This decorator limits the number of calls to a function within a given time period.
    If the limit is exceeded, the decorator will implement exponential backoff to
    prevent overwhelming the service.

    Args:
        max_calls: Maximum number of calls allowed in the period
        period: Time period in seconds
        backoff_factor: Multiplier for the exponential backoff
        max_backoff: Maximum backoff time in seconds
        jitter: Whether to add randomness to the backoff time

    Returns:
        Decorator function

    Examples:
        @rate_limit_decorator(max_calls=5, period=60)
        def fetch_data(url):
            # This function will be limited to 5 calls per 60 seconds
            # with exponential backoff if rate is exceeded
            return requests.get(url)

    """
    import random
    import threading
    import time
    from collections import deque
    from datetime import datetime, timedelta

    lock = threading.RLock()
    call_history = deque(maxlen=max_calls)
    backoff_until = None

    def decorator(func):
        # Use a separate function instead of @log_function_call to avoid recursion
        def wrapper(*args, **kwargs):
            nonlocal backoff_until

            rate_logger = get_logger("rate_limiter")

            with lock:
                now = datetime.now()

                # Check if we're in backoff mode
                if backoff_until and now < backoff_until:
                    wait_time = (backoff_until - now).total_seconds()
                    rate_logger.warning(f"Rate limit exceeded, backing off for {wait_time:.2f} seconds")
                    time.sleep(wait_time)
                    now = datetime.now()  # Update time after sleep

                # Clean up old calls outside the period
                while call_history and call_history[0] < now - timedelta(seconds=period):
                    call_history.popleft()

                # Check if we've exceeded the limit
                if len(call_history) >= max_calls:
                    # Calculate backoff time
                    backoff_time = min(period * (backoff_factor ** (len(call_history) - max_calls)), max_backoff)

                    # Add jitter if requested (±20%)
                    if jitter:
                        backoff_time *= random.uniform(0.8, 1.2)

                    backoff_until = now + timedelta(seconds=backoff_time)

                    rate_logger.warning(
                        f"Rate limit of {max_calls} calls per {period}s exceeded. Backing off for {backoff_time:.2f}s"
                    )

                    time.sleep(backoff_time)

                    # Clean up calls again after backoff
                    now = datetime.now()
                    while call_history and call_history[0] < now - timedelta(seconds=period):
                        call_history.popleft()

                # Record this call
                call_history.append(now)

            # Execute the function
            return func(*args, **kwargs)

        return wrapper

    return decorator


class RateLimiter:
    """Class-based rate limiter for more control over rate limiting behavior.

    This class provides methods to check rate limits and wait appropriate times
    before executing code, with support for multiple rate limit rules.

    Examples:
        # Create a rate limiter for a specific endpoint
        limiter = RateLimiter(name="api_client", max_calls=100, period=60)

        # Use the limiter before making a request
        with limiter:
            response = requests.get(url)

    """

    def __init__(
        self,
        name: str | None = None,
        max_calls: int = 60,
        period: float = 60,
        backoff_factor: float = 2.0,
        max_backoff: float = 60.0,
        jitter: bool = True,
    ):
        """Initialize a rate limiter.

        Args:
            name: Name for this rate limiter (for logging)
            max_calls: Maximum number of calls allowed in the period
            period: Time period in seconds
            backoff_factor: Multiplier for the exponential backoff
            max_backoff: Maximum backoff time in seconds
            jitter: Whether to add randomness to the backoff time

        """
        import threading
        from collections import deque

        self.name = name or "default"
        self.max_calls = max_calls
        self.period = period
        self.backoff_factor = backoff_factor
        self.max_backoff = max_backoff
        self.jitter = jitter

        self.logger = get_logger(f"rate_limiter.{self.name}")
        self.lock = threading.RLock()
        self.call_history = deque(maxlen=max_calls)
        self.backoff_until = None

    def __enter__(self):
        """Acquire the rate limit, waiting if necessary."""
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the rate limiter context."""
        # Nothing needed on exit
        return False

    def acquire(self):
        """Acquire the rate limit, waiting if necessary.

        Returns:
            The waiting time in seconds, or 0 if no waiting was needed.

        """
        import random
        import time
        from datetime import datetime, timedelta

        with self.lock:
            total_wait_time = 0

            # Main loop to handle backoff and rate limiting
            while True:
                now = datetime.now()

                # Check if we're in backoff mode
                if self.backoff_until and now < self.backoff_until:
                    wait_time = (self.backoff_until - now).total_seconds()
                    self.logger.warning(f"Rate limit exceeded, backing off for {wait_time:.2f} seconds")
                    time.sleep(wait_time)
                    total_wait_time += wait_time
                    now = datetime.now()  # Update after sleep

                # Clean up old calls outside the period
                while self.call_history and self.call_history[0] < now - timedelta(seconds=self.period):
                    self.call_history.popleft()

                # Check if we've exceeded the limit
                if len(self.call_history) >= self.max_calls:
                    # Calculate backoff time
                    backoff_time = min(
                        self.period * (self.backoff_factor ** (len(self.call_history) - self.max_calls)),
                        self.max_backoff,
                    )

                    # Add jitter if requested (±20%)
                    if self.jitter:
                        backoff_time *= random.uniform(0.8, 1.2)

                    self.backoff_until = now + timedelta(seconds=backoff_time)

                    self.logger.warning(
                        f"Rate limit of {self.max_calls} calls per {self.period}s exceeded. "
                        f"Backing off for {backoff_time:.2f}s"
                    )

                    time.sleep(backoff_time)
                    total_wait_time += backoff_time

                    # Continue the loop to recheck conditions after backoff
                    continue

                # If we get here, we're under the limit and can proceed
                # Record this call and return
                self.call_history.append(datetime.now())
                return total_wait_time

    def remaining(self):
        """Get the number of remaining calls allowed in the current period.

        Returns:
            Number of remaining calls allowed

        """
        from datetime import datetime, timedelta

        with self.lock:
            now = datetime.now()

            # Clean up old calls outside the period
            while self.call_history and self.call_history[0] < now - timedelta(seconds=self.period):
                self.call_history.popleft()

            return max(0, self.max_calls - len(self.call_history))

    def reset_in(self):
        """Get the number of seconds until the oldest call is removed from history.

        Returns:
            Seconds until reset, or 0 if no calls have been made

        """
        from datetime import datetime, timedelta

        with self.lock:
            if not self.call_history:
                return 0

            now = datetime.now()
            oldest = self.call_history[0]
            reset_time = oldest + timedelta(seconds=self.period)

            if reset_time <= now:
                return 0

            return (reset_time - now).total_seconds()


def throttle(max_calls: int = 1, period: float = 1.0):
    """Throttle throttling decorator that limits the call rate of a function.

    Unlike rate_limit_decorator, this doesn't implement exponential backoff,
    but simply ensures calls are spaced out by the minimum required interval.

    Args:
        max_calls: Maximum number of calls allowed in the period
        period: Time period in seconds

    Returns:
        Decorator function

    Examples:
        @throttle(max_calls=1, period=0.5)
        def make_request():
            # This function will be called at most once every 0.5 seconds
            return requests.get(url)

    """
    import threading
    import time
    from collections import deque
    from datetime import datetime, timedelta

    lock = threading.RLock()
    call_times = deque(maxlen=max_calls)
    min_interval = period / max_calls if max_calls > 0 else 0

    def decorator(func):
        # Use a separate function instead of @log_function_call to avoid recursion
        def wrapper(*args, **kwargs):
            nonlocal call_times

            with lock:
                now = datetime.now()

                # If we've made max_calls calls, calculate how long to wait
                if len(call_times) >= max_calls:
                    oldest_call = call_times.popleft()
                    next_call_time = oldest_call + timedelta(seconds=period)

                    if next_call_time > now:
                        sleep_time = (next_call_time - now).total_seconds()
                        time.sleep(sleep_time)

                # Even if we haven't made max_calls, ensure minimum interval
                # between consecutive calls
                if call_times and min_interval > 0:
                    last_call = call_times[-1]
                    min_next_call = last_call + timedelta(seconds=min_interval)

                    if min_next_call > now:
                        sleep_time = (min_next_call - now).total_seconds()
                        time.sleep(sleep_time)

                # Record this call
                call_times.append(datetime.now())

            # Execute the function
            return func(*args, **kwargs)

        return wrapper

    return decorator


def get_cache_dir(cache_dir: str | None = None) -> str:
    """Get and ensure the cache directory exists.

    Args:
        cache_dir: Override the default cache directory

    Returns:
        Absolute path to the cache directory

    Raises:
        CacheError: If the directory cannot be created

    """
    cache_path = os.path.abspath(cache_dir or DEFAULT_CACHE_DIR)

    try:
        os.makedirs(cache_path, exist_ok=True)
        return cache_path
    except OSError as e:
        raise CacheError(f"Failed to create cache directory: {e}") from e


def generate_cache_key(func_name: str, args: tuple, kwargs: dict) -> str:
    """Generate a unique cache key based on function name and arguments.

    Args:
        func_name: Name of the function being cached
        args: Positional arguments to the function
        kwargs: Keyword arguments to the function

    Returns:
        A hash string that can be used as a filename

    """
    # Create a string representation of the function call
    key_parts = [func_name]

    # Add string representations of args
    for arg in args:
        key_parts.extend(repr(arg).split("\n"))

    # Add string representations of kwargs (sorted for consistency)
    for k in sorted(kwargs.keys()):
        key_parts.extend(f"{k}={kwargs[k]!r}".split("\n"))

    # Join parts and hash
    key_str = "::".join(key_parts)
    return hashlib.md5(key_str.encode("utf-8")).hexdigest()


def cache_result(
    expire_seconds: int = 3600,
    cache_dir: str | None = None,
    key_prefix: str = "",
    exceptions_to_cache: list[type] | None = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Cache function results to disk with expiration.

    This decorator saves the result of a function call to disk and returns
    the cached value on subsequent calls with the same arguments, until
    the cache expires.

    Args:
        expire_seconds: Time in seconds until cached results expire
        cache_dir: Override the default cache directory
        key_prefix: Optional prefix for cache keys
        exceptions_to_cache: List of exception types to cache (None = don't cache exceptions)

    Returns:
        Decorator function

    Examples:
        @cache_result(expire_seconds=3600)  # Cache for 1 hour
        def fetch_event_data(event_id):
            # Expensive operation to fetch event data
            return data

        @cache_result(expire_seconds=86400, key_prefix="race_results_")
        def get_race_results(race_id):
            # Expensive operation to fetch race results
            return results

    """
    exceptions_to_cache = exceptions_to_cache or []

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        cache_logger = get_logger(f"cache.{func.__module__}")

        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            # Generate a unique key for this function call
            func_name = f"{key_prefix}{func.__name__}"
            cache_key = generate_cache_key(func_name, args, kwargs)

            try:
                # Ensure cache directory exists
                cache_path = get_cache_dir(cache_dir)
                cache_file = os.path.join(cache_path, cache_key)

                # Check if cache file exists and is not expired
                if os.path.exists(cache_file):
                    file_age = time.time() - os.path.getmtime(cache_file)

                    if file_age < expire_seconds:
                        # Cache hit - return cached result
                        cache_logger.debug(f"Cache hit for {func_name} ({file_age:.1f}s old)")
                        with open(cache_file, "rb") as f:
                            cached_data = pickle.load(f)

                            # If we cached an exception, re-raise it
                            if isinstance(cached_data, Exception):
                                cache_logger.debug(f"Re-raising cached exception: {type(cached_data).__name__}")
                                raise cached_data

                            return cast(T, cached_data)
                    else:
                        # Cache expired
                        cache_logger.debug(f"Cache expired for {func_name} ({file_age:.1f}s > {expire_seconds}s)")
                else:
                    cache_logger.debug(f"Cache miss for {func_name}")

                # Cache miss or expired - call the function
                try:
                    result = func(*args, **kwargs)

                    # Cache the result
                    with open(cache_file, "wb") as f:
                        pickle.dump(result, f)

                    return result

                except Exception as e:
                    # Only cache specific exception types if requested
                    if any(isinstance(e, exc_type) for exc_type in exceptions_to_cache):
                        cache_logger.debug(f"Caching exception: {type(e).__name__}")
                        with open(cache_file, "wb") as f:
                            pickle.dump(e, f)

                    # Re-raise the exception
                    raise

            except (OSError, pickle.PickleError) as cache_error:
                # If caching fails, log and continue without caching
                cache_logger.warning(f"Cache error: {cache_error}")
                return func(*args, **kwargs)

        return wrapper

    return decorator


class Cache:
    """Class-based cache utility for more direct control over caching operations.

    This class provides methods to manually get, set, check, and invalidate
    cached items without using the decorator approach.

    Examples:
        cache = Cache(expire_seconds=3600)

        # Try to get cached data
        result = cache.get('my_key')
        if result is None:
            # Cache miss, compute and store
            result = expensive_computation()
            cache.set('my_key', result)

    """

    def __init__(self, cache_dir: str | None = None, expire_seconds: int = 3600, namespace: str = ""):
        """Initialize a cache instance.

        Args:
            cache_dir: Override the default cache directory
            expire_seconds: Default expiration time in seconds
            namespace: Optional namespace to prefix all cache keys

        """
        self.cache_dir = cache_dir
        self.expire_seconds = expire_seconds
        self.namespace = namespace
        self.logger = get_logger(f"cache.{namespace}" if namespace else "cache")
        self._lock = threading.RLock()

    def _get_cache_path(self, key: str) -> str:
        """Get the full path for a cache key."""
        cache_dir = get_cache_dir(self.cache_dir)
        # Add namespace prefix to the key if specified
        prefixed_key = f"{self.namespace}::{key}" if self.namespace else key

        # Hash the key to ensure it's a valid filename
        hashed_key = hashlib.md5(prefixed_key.encode("utf-8")).hexdigest()
        return os.path.join(cache_dir, hashed_key)

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve an item from the cache.

        Args:
            key: Cache key to retrieve
            default: Value to return if key not found or expired

        Returns:
            The cached value or default

        """
        with self._lock:
            try:
                cache_file = self._get_cache_path(key)

                if os.path.exists(cache_file):
                    file_age = time.time() - os.path.getmtime(cache_file)

                    if file_age < self.expire_seconds:
                        # Cache hit
                        self.logger.debug(f"Cache hit for {key} ({file_age:.1f}s old)")
                        with open(cache_file, "rb") as f:
                            return pickle.load(f)
                    else:
                        # Cache expired
                        self.logger.debug(f"Cache expired for {key} ({file_age:.1f}s > {self.expire_seconds}s)")
                        # Optionally remove expired file
                        with contextlib.suppress(OSError):
                            os.remove(cache_file)
                else:
                    self.logger.debug(f"Cache miss for {key}")

                return default

            except (OSError, pickle.PickleError) as e:
                self.logger.warning(f"Cache retrieval error for {key}: {e}")
                return default

    def set(self, key: str, value: Any, expire_seconds: int | None = None) -> bool:
        """Store an item in the cache.

        Args:
            key: Cache key to store
            value: Value to cache
            expire_seconds: Override the default expiration time

        Returns:
            True if successful, False otherwise

        """
        with self._lock:
            try:
                cache_file = self._get_cache_path(key)

                with open(cache_file, "wb") as f:
                    pickle.dump(value, f)

                if expire_seconds is not None and expire_seconds != self.expire_seconds:
                    # If we have a custom expiration, we could track this in a metadata file
                    # but for simplicity, we'll just rely on the file modification time
                    pass

                self.logger.debug(f"Cache set for {key}")
                return True

            except (OSError, pickle.PickleError) as e:
                self.logger.warning(f"Cache storage error for {key}: {e}")
                return False

    def contains(self, key: str) -> bool:
        """Check if a key exists in the cache and is not expired.

        Args:
            key: Cache key to check

        Returns:
            True if key exists and is not expired

        """
        with self._lock:
            try:
                cache_file = self._get_cache_path(key)

                if os.path.exists(cache_file):
                    file_age = time.time() - os.path.getmtime(cache_file)
                    return file_age < self.expire_seconds

                return False

            except OSError as e:
                self.logger.warning(f"Cache check error for {key}: {e}")
                return False

    def delete(self, key: str) -> bool:
        """Delete a key from the cache.

        Args:
            key: Cache key to delete

        Returns:
            True if deleted, False otherwise

        """
        with self._lock:
            try:
                cache_file = self._get_cache_path(key)

                if os.path.exists(cache_file):
                    os.remove(cache_file)
                    self.logger.debug(f"Cache deleted for {key}")
                    return True

                return False

            except OSError as e:
                self.logger.warning(f"Cache deletion error for {key}: {e}")
                return False

    def clear(self, namespace_only: bool = True) -> int:
        """Clear all or namespace-specific cache entries.

        Args:
            namespace_only: If True, only clear entries in this namespace

        Returns:
            Number of cache entries cleared

        """
        with self._lock:
            try:
                cache_dir = get_cache_dir(self.cache_dir)
                count = 0

                for filename in os.listdir(cache_dir):
                    file_path = os.path.join(cache_dir, filename)

                    # Skip if not a file
                    if not os.path.isfile(file_path):
                        continue

                    # If namespace_only, check if this file belongs to our namespace
                    if namespace_only and self.namespace:
                        # We can't reliably determine if a file belongs to a namespace
                        # by examining its contents since it's pickled. Instead,
                        # we'll try to unpickle it safely, but if that fails, we
                        # should just use the filename which is a hash of our key
                        try:
                            # Use a simpler approach: create a test key with our namespace
                            # and see if the hash matches the filename
                            namespace_prefix = hashlib.md5(self.namespace.encode("utf-8")).hexdigest()[:6]
                            if not filename.startswith(namespace_prefix):
                                continue
                        except Exception:
                            # If we can't match it, be conservative and skip
                            continue

                    # Delete the file
                    try:
                        os.remove(file_path)
                        count += 1
                    except OSError:
                        pass

                self.logger.debug(f"Cleared {count} cache entries")
                return count

            except OSError as e:
                self.logger.warning(f"Cache clear error: {e}")
                return 0

    def get_stats(self) -> dict[str, Any]:
        """Get statistics about the cache.

        Returns:
            Dictionary with cache statistics

        """
        with self._lock:
            try:
                cache_dir = get_cache_dir(self.cache_dir)
                total_size = 0
                file_count = 0
                expired_count = 0
                oldest_file_age = 0
                newest_file_age = float("inf")
                now = time.time()

                for filename in os.listdir(cache_dir):
                    file_path = os.path.join(cache_dir, filename)

                    # Skip if not a file
                    if not os.path.isfile(file_path):
                        continue

                    # Skip if not in our namespace (if applicable)
                    if self.namespace:
                        try:
                            if not filename.startswith(hashlib.md5(self.namespace.encode("utf-8")).hexdigest()[:6]):
                                continue
                        except OSError:
                            continue

                    # Get file stats
                    try:
                        file_stat = os.stat(file_path)
                        file_size = file_stat.st_size
                        file_age = now - os.path.getmtime(file_path)  # Use getmtime directly for consistent expiry

                        total_size += file_size
                        file_count += 1

                        if file_age > self.expire_seconds:
                            expired_count += 1

                        oldest_file_age = max(oldest_file_age, file_age)
                        newest_file_age = min(newest_file_age, file_age)
                    except OSError:
                        pass

                # Handle edge case where no files were found
                if file_count == 0:
                    newest_file_age = 0

                return {
                    "file_count": file_count,
                    "total_size_bytes": total_size,
                    "expired_count": expired_count,
                    "oldest_file_age": oldest_file_age,
                    "newest_file_age": newest_file_age,
                    "cache_dir": cache_dir,
                    "namespace": self.namespace,
                    "default_expiration": self.expire_seconds,
                }

            except OSError as e:
                self.logger.warning(f"Cache stats error: {e}")
                return {
                    "error": str(e),
                    "cache_dir": self.cache_dir or DEFAULT_CACHE_DIR,
                    "namespace": self.namespace,
                    "default_expiration": self.expire_seconds,
                }


def clear_all_cache(cache_dir: str | None = None) -> int:
    """Clear all cache entries regardless of namespace.

    This is a convenience function to clear the entire cache directory.

    Args:
        cache_dir: Override the default cache directory

    Returns:
        Number of cache entries cleared

    """
    cache = Cache(cache_dir=cache_dir)
    return cache.clear(namespace_only=False)


def get_cached_value(
    key: str,
    producer_func: Callable[[], T],
    expire_seconds: int = 3600,
    cache_dir: str | None = None,
    namespace: str = "",
) -> T:
    """Get a cached value or compute it if not in cache.

    This is a more direct way to use caching without the decorator syntax.

    Args:
        key: Cache key to retrieve
        producer_func: Function to call to generate the value if not cached
        expire_seconds: Expiration time in seconds
        cache_dir: Override the default cache directory
        namespace: Optional namespace for the cache key

    Returns:
        The cached or newly computed value

    Examples:
        def fetch_expensive_data():
            # ... expensive operation ...
            return data

        # Get from cache or compute
        data = get_cached_value("my_expensive_data", fetch_expensive_data, expire_seconds=3600)

    """
    cache = Cache(cache_dir=cache_dir, expire_seconds=expire_seconds, namespace=namespace)

    # Try to get from cache
    value = cache.get(key)

    if value is None:
        # Cache miss - compute and store
        value = producer_func()
        cache.set(key, value)

    return value
