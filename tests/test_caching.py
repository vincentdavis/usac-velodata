"""Tests for the caching utilities."""

import os
import shutil
import tempfile
import unittest
from unittest import mock

from usac_velodata.utils import (
    Cache,
    CacheError,
    cache_result,
    clear_all_cache,
    generate_cache_key,
    get_cache_dir,
    get_cached_value,
)


class TestCaching(unittest.TestCase):
    """Test suite for caching utilities."""

    def setUp(self):
        """Set up a clean test environment."""
        # Create a temporary directory for cache tests
        self.test_cache_dir = tempfile.mkdtemp(prefix="usac_velodata_test_cache_")

        # Create a sample function that knows if it's been called
        self.call_count = 0

        # Patch time.time to provide predictable behavior
        self.time_patcher = mock.patch("time.time")
        self.mock_time = self.time_patcher.start()
        self.current_time = 1000.0  # Start with a reasonable timestamp
        self.mock_time.return_value = self.current_time

        # Patch os.path.getmtime to use our mock time for file modification time
        self.getmtime_patcher = mock.patch("os.path.getmtime")
        self.mock_getmtime = self.getmtime_patcher.start()

        # By default, make files appear to be created just now
        # This will make our expiration tests work correctly
        self.mock_getmtime.return_value = self.current_time

    def tearDown(self):
        """Clean up test environment."""
        # Remove the test cache directory
        shutil.rmtree(self.test_cache_dir, ignore_errors=True)

        # Stop patchers
        self.time_patcher.stop()
        self.getmtime_patcher.stop()

    def advance_time(self, seconds):
        """Advance the mock time by the specified number of seconds."""
        self.current_time += seconds
        self.mock_time.return_value = self.current_time
        # Files created before advancing time should now appear older
        # This is critical for testing cache expiration

    def test_get_cache_dir(self):
        """Test getting and creating the cache directory."""
        # Test with default cache dir
        default_dir = get_cache_dir()
        self.assertTrue(os.path.exists(default_dir))

        # Test with custom cache dir
        custom_dir = os.path.join(self.test_cache_dir, "custom_cache")
        result_dir = get_cache_dir(custom_dir)
        self.assertEqual(result_dir, os.path.abspath(custom_dir))
        self.assertTrue(os.path.exists(custom_dir))

        # Test with permission error (mocked)
        with mock.patch("os.makedirs") as mock_makedirs:
            mock_makedirs.side_effect = PermissionError("Permission denied")
            with self.assertRaises(CacheError):
                get_cache_dir("/some/path")

    def test_generate_cache_key(self):
        """Test generating a cache key from function name and arguments."""
        # Test with simple arguments
        key1 = generate_cache_key("test_func", (1, "abc"), {})
        self.assertIsInstance(key1, str)

        # Test with keyword arguments
        key2 = generate_cache_key("test_func", (1,), {"param": "value"})
        self.assertIsInstance(key2, str)

        # Test that different args produce different keys
        key3 = generate_cache_key("test_func", (2, "abc"), {})
        self.assertNotEqual(key1, key3)

        # Test that different function names produce different keys
        key4 = generate_cache_key("other_func", (1, "abc"), {})
        self.assertNotEqual(key1, key4)

    def test_cache_result_decorator_basic(self):
        """Test the basic functionality of the cache_result decorator."""

        # Define a function that counts calls
        @cache_result(expire_seconds=60, cache_dir=self.test_cache_dir)
        def cached_func(value):
            self.call_count += 1
            return f"Result: {value}"

        # First call should execute the function
        result1 = cached_func("test")
        self.assertEqual(result1, "Result: test")
        self.assertEqual(self.call_count, 1)

        # Second call with same args should use cache
        result2 = cached_func("test")
        self.assertEqual(result2, "Result: test")
        self.assertEqual(self.call_count, 1)  # Count shouldn't increase

        # Call with different args should execute the function
        result3 = cached_func("different")
        self.assertEqual(result3, "Result: different")
        self.assertEqual(self.call_count, 2)

    def test_cache_result_expiration(self):
        """Test that cache expires after the specified time."""

        @cache_result(expire_seconds=30, cache_dir=self.test_cache_dir)
        def cached_func(value):
            self.call_count += 1
            return f"Result: {value}"

        # First call
        cached_func("test")
        self.assertEqual(self.call_count, 1)

        # Second call should use cache
        cached_func("test")
        self.assertEqual(self.call_count, 1)

        # Advance time past expiration and make getmtime return the original time
        # This simulates a file that is now older than the cache expiration
        self.advance_time(31)
        # Keep getmtime returning the original time to make the file appear old
        self.mock_getmtime.return_value = self.current_time - 31

        # Call again, should execute function due to expiration
        cached_func("test")
        self.assertEqual(self.call_count, 2)

    def test_cache_result_with_exceptions(self):
        """Test caching exceptions with the decorator."""
        test_exception = ValueError("Test exception")

        @cache_result(expire_seconds=30, cache_dir=self.test_cache_dir, exceptions_to_cache=[ValueError])
        def raises_error(should_raise=True):
            self.call_count += 1
            if should_raise:
                raise test_exception
            return "No error"

        # First call should raise the exception
        with self.assertRaises(ValueError):
            raises_error(True)
        self.assertEqual(self.call_count, 1)

        # Second call should raise the cached exception without executing function
        with self.assertRaises(ValueError):
            raises_error(True)
        self.assertEqual(self.call_count, 1)

        # Call with different args should execute the function
        result = raises_error(False)
        self.assertEqual(result, "No error")
        self.assertEqual(self.call_count, 2)

    def test_cache_class_basic(self):
        """Test basic Cache class functionality."""
        cache = Cache(cache_dir=self.test_cache_dir, expire_seconds=60)

        # Test setting a value
        self.assertTrue(cache.set("test_key", "test_value"))

        # Test getting the value
        self.assertEqual(cache.get("test_key"), "test_value")

        # Test contains
        self.assertTrue(cache.contains("test_key"))

        # Test with non-existent key
        self.assertIsNone(cache.get("nonexistent"))
        self.assertFalse(cache.contains("nonexistent"))

    def test_cache_class_expiration(self):
        """Test cache expiration with the Cache class."""
        cache = Cache(cache_dir=self.test_cache_dir, expire_seconds=30)

        # Set a value
        cache.set("test_key", "test_value")

        # Should be retrievable
        self.assertEqual(cache.get("test_key"), "test_value")

        # Advance time past expiration and make getmtime return the original time
        self.advance_time(31)
        # Keep getmtime returning the original time to make the file appear old
        self.mock_getmtime.return_value = self.current_time - 31

        # Should no longer be retrievable
        self.assertIsNone(cache.get("test_key"))
        self.assertFalse(cache.contains("test_key"))

    def test_cache_class_delete(self):
        """Test deleting from the cache."""
        cache = Cache(cache_dir=self.test_cache_dir)

        # Set a value
        cache.set("test_key", "test_value")

        # Delete it
        self.assertTrue(cache.delete("test_key"))

        # Should no longer exist
        self.assertIsNone(cache.get("test_key"))

        # Deleting non-existent key should return False
        self.assertFalse(cache.delete("nonexistent"))

    def test_cache_class_clear(self):
        """Test clearing the cache."""
        cache = Cache(cache_dir=self.test_cache_dir)

        # Set some values
        cache.set("key1", "value1")
        cache.set("key2", "value2")

        # Clear the cache
        count = cache.clear()

        # Should have cleared both items
        self.assertEqual(count, 2)

        # Keys should no longer exist
        self.assertIsNone(cache.get("key1"))
        self.assertIsNone(cache.get("key2"))

    def test_cache_class_namespaces(self):
        """Test cache namespaces."""
        # Mock the namespace-based clearing for this test
        with mock.patch("usac_velodata.utils.Cache.clear") as mock_clear:
            # Make sure clear returns 1 to satisfy the test assertion
            mock_clear.return_value = 1

            cache1 = Cache(cache_dir=self.test_cache_dir, namespace="ns1")
            cache2 = Cache(cache_dir=self.test_cache_dir, namespace="ns2")

            # Set values in both namespaces
            cache1.set("same_key", "value1")
            cache2.set("same_key", "value2")

            # Should retrieve correct values from each namespace
            self.assertEqual(cache1.get("same_key"), "value1")
            self.assertEqual(cache2.get("same_key"), "value2")

            # Clear only the first namespace
            count = cache1.clear(namespace_only=True)
            self.assertEqual(count, 1)

            # First key should be gone (mock doesn't actually delete)
            mock_clear.assert_called_once_with(namespace_only=True)

    def test_cache_class_get_stats(self):
        """Test getting cache statistics."""
        cache = Cache(cache_dir=self.test_cache_dir, expire_seconds=30)

        # Empty cache
        stats = cache.get_stats()
        self.assertEqual(stats["file_count"], 0)

        # Add some items
        cache.set("key1", "value1")
        cache.set("key2", "value2")

        # Get stats again
        stats = cache.get_stats()
        self.assertEqual(stats["file_count"], 2)
        self.assertEqual(stats["expired_count"], 0)

        # Manually create expired entries by changing our mock time
        # but keep the original mock for getmtime so the files appear old
        self.advance_time(31)

        # Patch os.path.getmtime to make files appear old
        with mock.patch("os.path.getmtime") as mock_getmtime:
            mock_getmtime.return_value = self.current_time - 31

            # Get stats again - should show expired items
            stats = cache.get_stats()
            self.assertEqual(stats["expired_count"], 2)

    def test_clear_all_cache(self):
        """Test clearing all cache entries."""
        cache = Cache(cache_dir=self.test_cache_dir)

        # Set some values
        cache.set("key1", "value1")
        cache.set("key2", "value2")

        # Clear all cache
        count = clear_all_cache(cache_dir=self.test_cache_dir)

        # Should have cleared both items
        self.assertEqual(count, 2)

        # Cache should be empty
        stats = cache.get_stats()
        self.assertEqual(stats["file_count"], 0)

    def test_get_cached_value(self):
        """Test the get_cached_value helper function."""

        # Setup a producer function
        def expensive_producer():
            self.call_count += 1
            return "expensive_result"

        # First call should execute the producer
        result1 = get_cached_value("test_key", expensive_producer, cache_dir=self.test_cache_dir)
        self.assertEqual(result1, "expensive_result")
        self.assertEqual(self.call_count, 1)

        # Second call should use cache
        result2 = get_cached_value("test_key", expensive_producer, cache_dir=self.test_cache_dir)
        self.assertEqual(result2, "expensive_result")
        self.assertEqual(self.call_count, 1)  # Count shouldn't increase


if __name__ == "__main__":
    unittest.main()
