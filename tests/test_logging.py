"""Tests for the logging utilities."""

import json
import logging
import os
import tempfile
import unittest
from io import StringIO
from unittest import mock

from usac_velodata.utils import (
    LogContext,
    configure_logging,
    disable_logging,
    enable_debug_logging,
    get_logger,
    log_function_call,
    log_to_json,
)


class TestLoggingUtils(unittest.TestCase):
    """Test suite for logging utilities."""

    def setUp(self):
        """Set up test environment."""
        # Reset logging before each test
        root_logger = logging.getLogger("usac_velodata")
        root_logger.handlers = []
        root_logger.setLevel(logging.INFO)
        root_logger.propagate = False

        # Create temp file for logging tests
        self.log_file_fd, self.log_file_path = tempfile.mkstemp(suffix=".log")

    def tearDown(self):
        """Clean up after tests."""
        # Remove temp log file
        os.close(self.log_file_fd)
        if os.path.exists(self.log_file_path):
            os.unlink(self.log_file_path)

        # Reset logging
        disable_logging()

    def test_configure_logging_console_only(self):
        """Test configuring logging with console output only."""
        # Redirect stdout to capture logs
        with mock.patch("sys.stdout", new=StringIO()) as fake_stdout:
            configure_logging(level=logging.INFO, add_console_handler=True, log_file=None)

            logger = get_logger("test")
            logger.info("Test log message")

            output = fake_stdout.getvalue()
            self.assertIn("test - INFO - Test log message", output)

    def test_configure_logging_file_only(self):
        """Test configuring logging with file output only."""
        configure_logging(level=logging.INFO, log_file=self.log_file_path, add_console_handler=False)

        logger = get_logger("test")
        logger.info("Test file log message")

        with open(self.log_file_path) as f:
            log_content = f.read()
            self.assertIn("test - INFO - Test file log message", log_content)

    def test_configure_logging_custom_format(self):
        """Test configuring logging with custom format."""
        custom_format = "%(levelname)s [%(name)s]: %(message)s"

        with mock.patch("sys.stdout", new=StringIO()) as fake_stdout:
            configure_logging(level=logging.INFO, log_format=custom_format, add_console_handler=True)

            logger = get_logger("test")
            logger.info("Custom format test")

            output = fake_stdout.getvalue()
            self.assertIn("INFO [usac_velodata.test]: Custom format test", output)

    def test_get_logger(self):
        """Test getting loggers for different components."""
        logger1 = get_logger("component1")
        logger2 = get_logger("component2")

        self.assertEqual(logger1.name, "usac_velodata.component1")
        self.assertEqual(logger2.name, "usac_velodata.component2")
        self.assertNotEqual(logger1, logger2)

    def test_enable_debug_logging(self):
        """Test enabling debug logging."""
        with mock.patch("sys.stdout", new=StringIO()) as fake_stdout:
            enable_debug_logging()

            logger = get_logger("test")
            logger.debug("Debug message")
            logger.info("Info message")

            output = fake_stdout.getvalue()
            self.assertIn("DEBUG - Debug message", output)
            self.assertIn("INFO - Info message", output)

    def test_disable_logging(self):
        """Test disabling all logging."""
        with mock.patch("sys.stdout", new=StringIO()) as fake_stdout:
            # First enable logging
            configure_logging(level=logging.INFO)

            # Then disable it
            disable_logging()

            logger = get_logger("test")
            logger.error("This should not appear")

            output = fake_stdout.getvalue()
            self.assertEqual("", output)

    def test_log_function_call_decorator(self):
        """Test the log function call decorator."""
        with mock.patch("sys.stdout", new=StringIO()) as fake_stdout:
            configure_logging(level=logging.DEBUG)

            @log_function_call
            def test_function(a, b, c=None):
                return a + b

            result = test_function(1, 2, c="test")

            output = fake_stdout.getvalue()
            self.assertEqual(result, 3)
            self.assertIn("Calling test_function(1, 2, c='test')", output)
            self.assertIn("test_function returned successfully", output)

    def test_log_function_call_exception(self):
        """Test the log function call decorator with exception."""
        with mock.patch("sys.stdout", new=StringIO()) as fake_stdout:
            configure_logging(level=logging.DEBUG)

            @log_function_call
            def failing_function():
                raise ValueError("Test error")

            with self.assertRaises(ValueError):
                failing_function()

            output = fake_stdout.getvalue()
            self.assertIn("Calling failing_function()", output)
            self.assertIn("failing_function raised ValueError", output)

    def test_log_to_json(self):
        """Test logging in JSON format."""
        with mock.patch("sys.stdout", new=StringIO()) as fake_stdout:
            configure_logging(level=logging.INFO)

            log_to_json("Test JSON log", level="info", user_id=123, action="test")

            output = fake_stdout.getvalue()
            # Extract JSON from the log line
            json_str = output.split(" - ")[-1]
            log_data = json.loads(json_str)

            self.assertEqual(log_data["message"], "Test JSON log")
            self.assertEqual(log_data["level"], "INFO")
            self.assertEqual(log_data["user_id"], 123)
            self.assertEqual(log_data["action"], "test")

    def test_log_context_manager(self):
        """Test the logging context manager."""
        with mock.patch("sys.stdout", new=StringIO()) as fake_stdout:
            configure_logging(level=logging.INFO)

            with LogContext("Test Context", operation="save", entity_id=42):
                logger = get_logger("test")
                logger.info("Inside context")

            output = fake_stdout.getvalue()
            self.assertIn("Entered context: Test Context", output)
            self.assertIn("Inside context", output)
            self.assertIn("Exited context: Test Context", output)


if __name__ == "__main__":
    unittest.main()
