"""Tests for the RaceResultsParser class."""

import json
import os
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

from usac_velodata.exceptions import NetworkError
from usac_velodata.parser import RaceResultsParser


class TestRaceResultsParser(unittest.TestCase):
    """Tests for the RaceResultsParser class."""

    def setUp(self):
        """Set up test environment."""
        self.parser = RaceResultsParser(cache_enabled=False)

        # Path to test fixtures
        samples_dir = Path(os.path.dirname(os.path.dirname(__file__))) / "samples"

        # Race results fixture
        race_results_path = samples_dir / "race_results" / "1337864.html"
        if race_results_path.exists():
            try:
                with open(race_results_path, encoding="utf-8") as f:
                    self.race_results_json = json.load(f)
            except json.JSONDecodeError:
                # If there's an issue with control characters, use our fallback
                self.race_results_json = self._create_test_race_results()
        else:
            self.race_results_json = self._create_test_race_results()

        # Load info fixture
        load_info_path = samples_dir / "load_info" / "132893.html"
        if load_info_path.exists():
            try:
                with open(load_info_path, encoding="utf-8") as f:
                    self.load_info_json = json.load(f)
            except json.JSONDecodeError:
                # If there's an issue with control characters, use our fallback
                self.load_info_json = self._create_test_load_info()
        else:
            self.load_info_json = self._create_test_load_info()

    def _create_test_race_results(self):
        """Create test race results data."""
        return {
            "error": False,
            "message": """
            <div class='table'>
                <div class='tablerow odd'>
                    <div class='tablecell results'><img src='/images/medal1st.png'></div>
                    <div class='tablecell results'>1</div>
                    <div class='tablecell results'></div>
                    <div class='tablecell results'></div>
                    <div class='tablecell results'><a href='javascript:void(0)'>John Doe</a></div>
                    <div class='tablecell results'>Boulder, CO</div>
                    <div class='tablecell results'>01:01:07</div>
                    <div class='tablecell results'></div>
                    <div class='tablecell results'>12345</div>
                    <div class='tablecell results'>101</div>
                    <div class='tablecell results'>Team Alpha</div>
                </div>
                <div class='tablerow even'>
                    <div class='tablecell results'><img src='/images/medal2nd.png'></div>
                    <div class='tablecell results'>2</div>
                    <div class='tablecell results'></div>
                    <div class='tablecell results'></div>
                    <div class='tablecell results'><a href='javascript:void(0)'>Jane Smith</a></div>
                    <div class='tablecell results'>Denver, CO</div>
                    <div class='tablecell results'>01:01:25</div>
                    <div class='tablecell results'></div>
                    <div class='tablecell results'>23456</div>
                    <div class='tablecell results'>102</div>
                    <div class='tablecell results'>Team Beta</div>
                </div>
            </div>
            """,
        }

    def _create_test_load_info(self):
        """Create test load info data."""
        return {
            "error": False,
            "message": """
            <h3>USA Cycling December VRL<br/>Colorado Springs, CO<br/>Dec 2, 2020 - Dec 30, 2020</h3>
            <b>Cross Country Ultra Endurance 12/02/2020</b>
            <ul id="results_list">
                <li id='race_1337864'><a href='javascript:void(0)'>XCU Men 1:55 Category A</a></li>
                <li id='race_1337865'><a href='javascript:void(0)'>XCU Men 1:55 Category B</a></li>
            </ul>
            """,
        }

    @mock.patch("usac_velodata.parser.BaseParser.fetch_race_results")
    def test_parse(self, mock_fetch):
        """Test parsing race results."""
        # Mock the fetch_race_results method
        mock_fetch.return_value = {
            "id": "1337864",
            "riders": [
                {
                    "place": "1",
                    "name": "John Doe",
                    "team": "Team A"
                }
            ]
        }
        
        # Parse the race results
        race_results = self.parser.parse("1337864")
        
        # Verify race results were parsed correctly
        self.assertIsInstance(race_results, dict)
        self.assertEqual(race_results["id"], "1337864")
        
        # Check that riders were extracted
        self.assertGreater(len(race_results["riders"]), 0)
        self.assertEqual(race_results["riders"][0]["name"], "John Doe")

    @mock.patch("usac_velodata.parser.BaseParser.fetch_race_results")
    def test_parse_empty_results(self, mock_fetch):
        """Test parsing empty race results."""
        # Mock empty response
        mock_fetch.return_value = {"error": False, "message": "<div class='table'></div>"}

        # Parse the race results
        race_results = self.parser.parse("1337864")

        # Verify basic structure is correct
        self.assertIsInstance(race_results, dict)
        self.assertEqual(race_results["id"], "1337864")
        self.assertEqual(race_results["riders"], [])

    @mock.patch("usac_velodata.parser.BaseParser.fetch_race_results")
    def test_network_error(self, mock_fetch):
        """Test handling of network errors during race results parsing."""
        # Mock network error
        mock_fetch.side_effect = NetworkError("Failed to fetch race results")

        # Verify NetworkError is raised
        with self.assertRaises(NetworkError):
            self.parser.parse("1337864")

    @mock.patch("usac_velodata.parser.BaseParser.fetch_load_info")
    def test_parse_race_categories(self, mock_fetch):
        """Test parsing race categories from load info."""
        # Mock the fetch_load_info method
        mock_fetch.return_value = {
            "categories": [
                {
                    "id": "1337864",
                    "name": "XCU Men 1:55 Category A",
                    "discipline": "Cross Country Ultra Endurance",
                    "gender": "Men",
                    "category_rank": "A"
                }
            ]
        }
        
        # Parse the race categories
        categories = self.parser.parse_race_categories("132893", "Cross Country Ultra Endurance 12/02/2020")
        
        # Verify categories were parsed correctly
        self.assertIsInstance(categories, list)
        self.assertGreater(len(categories), 0)
        
        # Check details of the first category
        first_category = categories[0]
        self.assertEqual(first_category["name"], "XCU Men 1:55 Category A")
        self.assertEqual(first_category["gender"], "Men")
        self.assertEqual(first_category["category_rank"], "A")

    @mock.patch("usac_velodata.parser.BaseParser.fetch_load_info")
    def test_parse_empty_categories(self, mock_fetch):
        """Test parsing empty race categories."""
        # Mock empty response
        mock_fetch.return_value = {"error": False, "message": "<ul id='results_list'></ul>"}

        # Parse the race categories
        categories = self.parser.parse_race_categories("132893", "Cross Country Ultra Endurance 12/02/2020")

        # Verify empty list is returned
        self.assertEqual(categories, [])

    @mock.patch("usac_velodata.parser.RaceResultsParser.parse")
    def test_get_race_results(self, mock_parse):
        """Test getting race results with category information."""
        # Mock the parse method
        mock_parse.return_value = {
            "id": "1337864",
            "category": {},
            "riders": [{"place": "1", "name": "John Doe"}],
            "event_id": None,
            "date": None,
        }

        # Define category info
        category_info = {
            "id": "1337864",
            "name": "XCU Men 1:55 Category A",
            "discipline": "Cross Country Ultra Endurance",
            "event_id": "2020-26",
            "race_date": date(2020, 12, 2),
        }

        # Get the race results with category info
        race_results = self.parser.get_race_results("1337864", category_info)

        # Verify results have category info incorporated
        self.assertEqual(race_results["category"]["name"], "XCU Men 1:55 Category A")
        self.assertEqual(race_results["event_id"], "2020-26")
        self.assertEqual(race_results["date"], date(2020, 12, 2))

if __name__ == "__main__":
    unittest.main()
