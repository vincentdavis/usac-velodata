"""Tests for the rate limiting utilities."""

import unittest
from datetime import datetime, timedelta
from unittest import mock

from usac_velodata.utils import RateLimiter, rate_limit_decorator, throttle


class TestRateLimiting(unittest.TestCase):
    """Test suite for rate limiting utilities."""

    def setUp(self):
        """Set up test environment."""
        # Mock datetime.now() for predictable testing
        self.datetime_patcher = mock.patch("datetime.datetime")
        self.mock_datetime = self.datetime_patcher.start()

        # Start with a fixed time
        self.current_time = datetime(2023, 1, 1, 12, 0, 0)
        self.mock_datetime.now.return_value = self.current_time

        # Make datetime.now a side_effect function that updates time on each call
        def side_effect_time():
            return self.current_time

        self.mock_datetime.now.side_effect = side_effect_time

        # Mock other datetime methods that might be used
        self.mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

        # Also patch time.sleep to prevent actual sleeping
        self.sleep_patcher = mock.patch("time.sleep")
        self.mock_sleep = self.sleep_patcher.start()

        # Make sleep advance the mock time
        def sleep_side_effect(seconds):
            self.advance_time(seconds)

        self.mock_sleep.side_effect = sleep_side_effect

    def tearDown(self):
        """Clean up after tests."""
        self.datetime_patcher.stop()
        self.sleep_patcher.stop()

    def advance_time(self, seconds):
        """Advance the mock time by the specified number of seconds."""
        self.current_time += timedelta(seconds=seconds)

    def test_rate_limit_decorator_basic(self):
        """Test rate limit decorator with basic functionality."""
        counter = 0

        @rate_limit_decorator(max_calls=2, period=10, jitter=False)
        def test_func():
            nonlocal counter
            counter += 1
            return counter

        # First two calls should not be rate limited
        self.assertEqual(test_func(), 1)
        self.assertEqual(test_func(), 2)

        # Third call should cause rate limiting
        self.assertEqual(test_func(), 3)

        # Sleep should have been called at least once
        self.assertTrue(self.mock_sleep.call_count >= 1)

    def test_throttle_decorator(self):
        """Test the throttle decorator."""
        counter = 0

        @throttle(max_calls=2, period=1.0)
        def test_func():
            nonlocal counter
            counter += 1
            return counter

        # First call should not be throttled
        self.assertEqual(test_func(), 1)

        # Second call should be under the limit
        self.assertEqual(test_func(), 2)

        # Third call should be throttled
        self.assertEqual(test_func(), 3)

        # Time.sleep should have been called at least once
        self.assertTrue(self.mock_sleep.call_count >= 1)

    def test_rate_limiter_basic(self):
        """Test basic RateLimiter class functionality."""
        # Create a rate limiter with no jitter for predictable testing
        limiter = RateLimiter(max_calls=2, period=10, jitter=False)

        # First two calls should not wait
        self.assertEqual(limiter.acquire(), 0)
        self.assertEqual(limiter.acquire(), 0)

        # Third call should cause waiting
        wait_time = limiter.acquire()
        self.assertTrue(wait_time > 0)

        # Sleep should have been called
        self.assertTrue(self.mock_sleep.call_count >= 1)

    def test_rate_limiter_context(self):
        """Test RateLimiter as a context manager."""
        # Create a rate limiter with no jitter for predictable testing
        limiter = RateLimiter(max_calls=2, period=10, jitter=False)

        # First two calls should not wait
        with limiter:
            pass

        with limiter:
            pass

        # Third call should wait
        with limiter:
            pass

        # Sleep should have been called
        self.assertTrue(self.mock_sleep.call_count >= 1)

    def test_limiter_remaining(self):
        """Test getting remaining capacity from RateLimiter."""
        limiter = RateLimiter(max_calls=3, period=10)

        # Initially should have 3 remaining calls
        self.assertEqual(limiter.remaining(), 3)

        # After one call, should have 2 remaining
        limiter.acquire()
        self.assertEqual(limiter.remaining(), 2)

        # After a second call, should have 1 remaining
        limiter.acquire()
        self.assertEqual(limiter.remaining(), 1)

        # After using all calls, should have 0 remaining
        limiter.acquire()
        self.assertEqual(limiter.remaining(), 0)

        # After waiting for the period to expire, should reset
        self.advance_time(11)  # Advance past the period
        self.assertEqual(limiter.remaining(), 3)

    def test_limiter_reset_in(self):
        """Test the reset_in method of RateLimiter."""
        limiter = RateLimiter(max_calls=2, period=10)

        # If no calls made, reset_in should return 0
        self.assertEqual(limiter.reset_in(), 0)

        # Make a call and check reset time
        limiter.acquire()
        self.assertLessEqual(limiter.reset_in(), 10)

        # Advance time and check again
        self.advance_time(5)
        self.assertLessEqual(limiter.reset_in(), 5)

        # Advance past reset time
        self.advance_time(6)
        self.assertEqual(limiter.reset_in(), 0)


if __name__ == "__main__":
    unittest.main()
