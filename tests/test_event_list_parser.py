"""Tests for the EventListParser class."""

import os
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

from usac_velodata.exceptions import NetworkError
from usac_velodata.parser import EventListParser


class TestEventListParser(unittest.TestCase):
    """Tests for the EventListParser class."""

    def setUp(self):
        """Set up test environment."""
        self.parser = EventListParser(cache_enabled=False)

        # Path to test fixture
        samples_dir = Path(os.path.dirname(os.path.dirname(__file__))) / "samples"
        self.fixture_path = samples_dir / "event_lists" / "colorado_2020.html"

        # Sample event list HTML
        if self.fixture_path.exists():
            with open(self.fixture_path, encoding="utf-8") as f:
                self.event_list_html = f.read()
        else:
            # Create a minimal event HTML for tests if fixture doesn't exist
            self.event_list_html = """
            <table class='datatable'>
                <tr><th>Header 1</th></tr>
                <tr><th>Header 2</th><th>Race Date</th><th>Event Name</th><th>Submit Date</th></tr>
                <tr><td></td>
                    <td align='right'>12/02/2020</td>
                    <td><a href='/results/?permit=2020-26'>USA Cycling December VRL</a></td>
                    <td align='right'>12/18/2020</td></tr>
                <tr><td></td>
                    <td align='right'>11/14/2020</td>
                    <td><a href='/results/?permit=2020-2882'>CYCLO-X Parker</a></td>
                    <td align='right'>11/15/2020</td></tr>
            </table>
            """

    @mock.patch("usac_velodata.parser.BaseParser.fetch_event_list")
    def test_parse(self, mock_fetch):
        """Test parsing event listings."""
        # Mock the fetch_event_list method to return our sample HTML
        mock_fetch.return_value = self.event_list_html

        # Parse the events
        events = self.parser.parse("CO", 2020)

        # Verify events were parsed correctly
        self.assertIsInstance(events, list)
        self.assertGreater(len(events), 0)

        # Check the first event
        event = events[0]
        self.assertIn("event_date", event)
        self.assertIn("name", event)
        self.assertIn("permit", event)
        self.assertIn("permit_url", event)

        # Verify specific values
        self.assertEqual(event["name"], "USA Cycling December VRL")
        self.assertEqual(event["permit"], "2020-26")
        self.assertEqual(event["event_date"], date(2020, 12, 2))

    @mock.patch("usac_velodata.parser.BaseParser.fetch_event_list")
    def test_parse_empty_table(self, mock_fetch):
        """Test parsing event listings with empty table."""
        # Mock the fetch_event_list method to return an empty table
        mock_fetch.return_value = """
        <table class='datatable'>
            <tr><th>Header 1</th></tr>
            <tr><th>Header 2</th><th>Race Date</th><th>Event Name</th><th>Submit Date</th></tr>
        </table>
        """

        # Parse the events
        events = self.parser.parse("CO", 2020)

        # Verify an empty list is returned
        self.assertEqual(events, [])

    @mock.patch("usac_velodata.parser.BaseParser.fetch_event_list")
    def test_parse_no_table(self, mock_fetch):
        """Test parsing event listings with no table."""
        # Mock the fetch_event_list method to return HTML with no table
        mock_fetch.return_value = """
        <div>No table here</div>
        """

        # Parse the events
        events = self.parser.parse("CO", 2020)

        # Verify an empty list is returned
        self.assertEqual(events, [])

    @mock.patch("usac_velodata.parser.BaseParser.fetch_event_list")
    def test_get_events(self, mock_fetch):
        """Test getting events with IDs and state/year added."""
        # Mock the fetch_event_list method to return our sample HTML
        mock_fetch.return_value = self.event_list_html

        # Get the events
        events = self.parser.get_events("CO", 2020)

        # Verify events were parsed correctly
        self.assertIsInstance(events, list)
        self.assertGreater(len(events), 0)

        # Check the first event has the additional fields
        event = events[0]
        self.assertIn("id", event)
        self.assertIn("state", event)
        self.assertIn("year", event)

        # Verify specific values
        self.assertEqual(event["id"], "2020-26")  # ID from permit
        self.assertEqual(event["state"], "CO")
        self.assertEqual(event["year"], 2020)

    @mock.patch("usac_velodata.parser.BaseParser.fetch_event_list")
    def test_get_events_no_permit(self, mock_fetch):
        """Test getting events with no permit numbers."""
        # Mock the fetch_event_list method to return HTML with no permit numbers
        mock_fetch.return_value = """
        <table class='datatable'>
            <tr><th>Header 1</th></tr>
            <tr><th>Header 2</th><th>Race Date</th><th>Event Name</th><th>Submit Date</th></tr>
            <tr><td></td>
                <td align='right'>12/02/2020</td>
                <td><a href='/results/'>USA Cycling December VRL</a></td>
                <td align='right'>12/18/2020</td></tr>
        </table>
        """

        # Get the events
        events = self.parser.get_events("CO", 2020)

        # Verify events were parsed correctly
        self.assertIsInstance(events, list)
        self.assertEqual(len(events), 1)

        # Check ID is generated from name, date, and state
        event = events[0]
        self.assertIn("id", event)
        self.assertTrue(event["id"].startswith("usa_cycling_december"))
        self.assertTrue("2020-12-02" in event["id"])
        self.assertTrue("CO" in event["id"])

    @mock.patch("usac_velodata.parser.BaseParser.fetch_event_list")
    def test_network_error(self, mock_fetch):
        """Test handling network errors."""
        # Mock the fetch_event_list method to raise a NetworkError
        mock_fetch.side_effect = NetworkError("Failed to fetch event list")

        # Verify NetworkError is raised
        with self.assertRaises(NetworkError):
            self.parser.parse("CO", 2020)


if __name__ == "__main__":
    unittest.main()
