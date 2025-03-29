"""Tests for the command-line interface."""

import io
import unittest
from datetime import date
from unittest import mock

from usac_velodata.cli import format_output, main, parse_args
from usac_velodata.models import Event


class TestArgumentParsing(unittest.TestCase):
    """Tests for CLI argument parsing."""

    def test_version_argument(self):
        """Test version argument."""
        with self.assertRaises(SystemExit) as cm:
            parse_args(["--version"])
        self.assertEqual(cm.exception.code, 0)

    def test_events_command(self):
        """Test events command arguments."""
        args = parse_args(["events", "--state", "CA", "--year", "2020"])
        self.assertEqual(args.command, "events")
        self.assertEqual(args.state, "CA")
        self.assertEqual(args.year, 2020)
        self.assertEqual(args.output, "json")
        self.assertFalse(args.pretty)

    def test_events_command_defaults(self):
        """Test events command with default values."""
        current_year = date.today().year
        args = parse_args(["events", "--state", "CA"])
        self.assertEqual(args.command, "events")
        self.assertEqual(args.state, "CA")
        self.assertEqual(args.year, current_year)
        self.assertEqual(args.output, "json")
        self.assertFalse(args.pretty)

    def test_results_command(self):
        """Test results command arguments."""
        args = parse_args(["results", "--race-id", "12345"])
        self.assertEqual(args.command, "results")
        self.assertEqual(args.race_id, "12345")
        self.assertEqual(args.output, "json")
        self.assertFalse(args.pretty)

    def test_details_command(self):
        """Test details command arguments."""
        args = parse_args(["details", "--permit", "2020-123"])
        self.assertEqual(args.command, "details")
        self.assertEqual(args.permit, "2020-123")
        self.assertEqual(args.output, "json")
        self.assertFalse(args.pretty)

    def test_disciplines_command(self):
        """Test disciplines command arguments."""
        args = parse_args(["disciplines", "--permit", "2020-123"])
        self.assertEqual(args.command, "disciplines")
        self.assertEqual(args.permit, "2020-123")
        self.assertEqual(args.output, "json")
        self.assertFalse(args.pretty)

    def test_categories_command(self):
        """Test categories command arguments."""
        args = parse_args(["categories", "--info-id", "12345", "--label", "Road Race"])
        self.assertEqual(args.command, "categories")
        self.assertEqual(args.info_id, "12345")
        self.assertEqual(args.label, "Road Race")
        self.assertEqual(args.output, "json")
        self.assertFalse(args.pretty)

    def test_complete_command(self):
        """Test complete command arguments."""
        args = parse_args(["complete", "--permit", "2020-123"])
        self.assertEqual(args.command, "complete")
        self.assertEqual(args.permit, "2020-123")
        self.assertEqual(args.output, "json")
        self.assertFalse(args.pretty)
        self.assertFalse(args.no_results)

    def test_global_options(self):
        """Test global options."""
        args = parse_args(
            [
                "--cache-dir",
                "/tmp/cache",
                "--no-cache",
                "--no-rate-limit",
                "--log-level",
                "DEBUG",
                "events",
                "--state",
                "CA",
            ]
        )
        self.assertEqual(args.cache_dir, "/tmp/cache")
        self.assertTrue(args.no_cache)
        self.assertTrue(args.no_rate_limit)
        self.assertEqual(args.log_level, "DEBUG")
        self.assertEqual(args.command, "events")
        self.assertEqual(args.state, "CA")


class TestFormatOutput(unittest.TestCase):
    """Tests for output formatting."""

    def test_json_output(self):
        """Test JSON output formatting."""
        event = Event(
            id="2020-123",
            name="Test Event",
            permit_number="2020-123",
            date=date(2020, 1, 1),
            location="Test Location",
            state="CA",
            year=2020,
        )
        output = format_output(event, "json")
        self.assertIn('"id": "2020-123"', output)
        self.assertIn('"name": "Test Event"', output)

    def test_json_pretty_output(self):
        """Test pretty-printed JSON output."""
        event = Event(
            id="2020-123",
            name="Test Event",
            permit_number="2020-123",
            date=date(2020, 1, 1),
            location="Test Location",
            state="CA",
            year=2020,
        )
        output = format_output(event, "json", pretty=True)
        self.assertIn('  "id": "2020-123"', output)
        self.assertIn('  "name": "Test Event"', output)

    def test_csv_output(self):
        """Test CSV output formatting."""
        event = Event(
            id="2020-123",
            name="Test Event",
            permit_number="2020-123",
            date=date(2020, 1, 1),
            location="Test Location",
            state="CA",
            year=2020,
        )
        output = format_output(event, "csv")
        # Check for the presence of headers and data, not the exact order
        self.assertIn("id", output)
        self.assertIn("name", output)
        self.assertIn("permit_number", output)
        self.assertIn("date", output)
        self.assertIn("location", output)
        self.assertIn("state", output)
        self.assertIn("year", output)
        self.assertIn("2020-123", output)
        self.assertIn("Test Event", output)
        self.assertIn("2020-01-01", output)
        self.assertIn("Test Location", output)

    def test_invalid_format(self):
        """Test invalid output format."""
        event = Event(
            id="2020-123",
            name="Test Event",
            permit_number="2020-123",
            date=date(2020, 1, 1),
            location="Test Location",
            state="CA",
            year=2020,
        )
        with self.assertRaises(ValueError):
            format_output(event, "invalid")


class TestMainFunction(unittest.TestCase):
    """Tests for the main CLI function."""

    @mock.patch("sys.stdout", new_callable=io.StringIO)
    @mock.patch("usac_velodata.cli.USACyclingClient")
    def test_events_command(self, mock_client_class, mock_stdout):
        """Test events command execution."""
        # Create a mock client instance
        mock_client = mock.MagicMock()
        mock_client_class.return_value = mock_client

        # Mock the get_events method to return a list of events
        mock_client.get_events.return_value = [
            Event(
                id="2020-123",
                name="Test Event",
                permit_number="2020-123",
                date=date(2020, 1, 1),
                location="Test Location",
                state="CA",
                year=2020,
            )
        ]

        # Call the main function with the events command
        result = main(["events", "--state", "CA", "--year", "2020"])

        # Verify the client was created with the correct arguments
        mock_client_class.assert_called_once_with(
            cache_enabled=True,
            cache_dir=None,
            rate_limit=True,
            log_level="INFO",
        )

        # Verify the get_events method was called with the correct arguments
        mock_client.get_events.assert_called_once_with("CA", 2020)

        # Verify the output contains the event information
        output = mock_stdout.getvalue()
        self.assertIn('"id": "2020-123"', output)
        self.assertIn('"name": "Test Event"', output)

        # Verify the function returned success
        self.assertEqual(result, 0)

    @mock.patch("sys.stderr", new_callable=io.StringIO)
    @mock.patch("usac_velodata.cli.USACyclingClient")
    def test_events_command_validation_error(self, mock_client_class, mock_stderr):
        """Test events command with validation error."""
        # Create a mock client instance
        mock_client = mock.MagicMock()
        mock_client_class.return_value = mock_client

        # Mock the get_events method to raise a ValidationError
        from usac_velodata.exceptions import ValidationError

        mock_client.get_events.side_effect = ValidationError("Invalid state code")

        # Call the main function with the events command
        result = main(["events", "--state", "CA", "--year", "2020"])

        # Verify the error message was printed to stderr
        error_output = mock_stderr.getvalue()
        self.assertIn("Error: Invalid state code", error_output)

        # Verify the function returned an error code
        self.assertEqual(result, 1)

    @mock.patch("sys.stdout", new_callable=io.StringIO)
    @mock.patch("usac_velodata.cli.USACyclingClient")
    def test_complete_command(self, mock_client_class, mock_stdout):
        """Test complete command execution."""
        # Create a mock client instance
        mock_client = mock.MagicMock()
        mock_client_class.return_value = mock_client

        # Mock the get_complete_event_data method to return event data
        mock_client.get_complete_event_data.return_value = {
            "event": {
                "id": "2020-123",
                "name": "Test Event",
            },
            "disciplines": [{"id": "12345", "name": "Road Race"}],
            "categories": {},
            "results": {},
        }

        # Call the main function with the complete command
        result = main(["complete", "--permit", "2020-123", "--pretty"])

        # Verify the get_complete_event_data method was called correctly
        mock_client.get_complete_event_data.assert_called_once_with("2020-123", True)

        # Verify the output contains the event information
        output = mock_stdout.getvalue()
        self.assertIn('"event": {', output)
        self.assertIn('"id": "2020-123"', output)
        self.assertIn('"disciplines": [', output)

        # Verify the function returned success
        self.assertEqual(result, 0)


if __name__ == "__main__":
    unittest.main()
