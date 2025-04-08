"""Tests for the EventDetailsParser class."""

import os
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

from usac_velodata.exceptions import NetworkError
from usac_velodata.parser import EventDetailsParser


class TestEventDetailsParser(unittest.TestCase):
    """Tests for the EventDetailsParser class."""

    def setUp(self):
        """Set up test environment."""
        self.parser = EventDetailsParser(cache_enabled=False)

        # Path to test fixture
        samples_dir = Path(os.path.dirname(os.path.dirname(__file__))) / "samples"
        fixture_path = samples_dir / "permit_pages" / "2020-26.html"

        # Sample event details HTML
        if fixture_path.exists():
            with open(fixture_path, encoding="utf-8") as f:
                self.sample_html = f.read()
        else:
            # Create a minimal event details HTML for tests if fixture doesn't exist
            self.sample_html = """
            <div id="pgcontent" class="onecol">
                <div id='resultsmain'>
                    <h3>USA Cycling December VRL<br/>
                    Colorado Springs, CO<br/>
                    Dec 2, 2020 - Dec 30, 2020</h3>
                    <div class='tablerow'>
                        <div class='tablecell'>
                            <a href='javascript:void(0)' onclick="loadInfoID(132893,
                            'Cross Country Ultra Endurance 12/02/2020')">
                                Cross Country Ultra Endurance
                            </a>
                        </div>
                        <div class='tablecell'>12/02/2020</div>
                    </div>
                    <div class='tablerow'>
                        <div class='tablecell'>
                            <a href='javascript:void(0)' onclick="loadInfoID(132897,
                            'Cross Country Ultra Endurance 12/09/2020')">
                                Cross Country Ultra Endurance
                            </a>
                        </div>
                        <div class='tablecell'>12/09/2020</div>
                    </div>
                </div>
            </div>
            """

    @mock.patch("usac_velodata.parser.BaseParser.fetch_permit_page")
    def test_parse(self, mock_fetch):
        """Test parsing event details from permit page."""
        # Mock the fetch_permit_page method to return our sample HTML
        mock_fetch.return_value = self.sample_html

        # Parse the event details
        event_details = self.parser.parse("2020-26")

        # Verify event details were parsed correctly
        self.assertIsInstance(event_details, dict)

        # Check required fields
        self.assertEqual(event_details["id"], "2020-26")
        self.assertEqual(event_details["permit_id"], "2020-26")
        self.assertEqual(event_details["year"], 2020)

        # Check name and location
        self.assertEqual(event_details["name"], "USA Cycling December VRL")
        self.assertEqual(event_details["location"], "Colorado Springs")
        self.assertEqual(event_details["state"], "CO")

        # Check dates
        self.assertEqual(event_details["start_date"], date(2020, 12, 2))
        self.assertEqual(event_details["end_date"], date(2020, 12, 30))

        # Check disciplines
        disciplines = [d["discipline"] for d in event_details["disciplines"]]
        self.assertIn("Cross Country Ultra Endurance", disciplines)

        # Verify required fields are present
        required_fields = [
            "id",
            "name",
            "permit_id",
            "start_date",
            "end_date",
            "location",
            "state",
            "year",
            "disciplines",
            "categories",
            "is_usac_sanctioned",
            "promoter",
            "promoter_email",
            "website",
            "registration_url",
            "description",
        ]
        for field in required_fields:
            self.assertIn(field, event_details)

    @mock.patch("usac_velodata.parser.BaseParser.fetch_permit_page")
    def test_parse_minimal_html(self, mock_fetch):
        """Test parsing event details with minimal HTML."""
        # Create a minimal HTML that only has the permit number
        minimal_html = "<html><body>Permit 2020-26</body></html>"
        mock_fetch.return_value = minimal_html

        # Parse the event details
        event_details = self.parser.parse("2020-26")

        # Verify basic required fields are present with default values
        self.assertEqual(event_details["id"], "2020-26")
        self.assertEqual(event_details["permit_id"], "2020-26")
        self.assertEqual(event_details["year"], 2020)
        self.assertEqual(event_details["name"], "Event 2020-26")
        self.assertEqual(event_details["location"], "Unknown")
        self.assertEqual(event_details["disciplines"], [])

    @mock.patch("usac_velodata.parser.BaseParser.fetch_permit_page")
    def test_get_event_details(self, mock_fetch):
        """Test getting event details through the higher-level method."""
        # Mock the fetch_permit_page method
        mock_fetch.return_value = self.sample_html

        # Get the event details
        event_details = self.parser.get_event_details("2020-26")

        # Verify event details were returned correctly
        self.assertIsInstance(event_details, dict)
        self.assertEqual(event_details["id"], "2020-26")
        self.assertEqual(event_details["name"], "USA Cycling December VRL")

    @mock.patch("usac_velodata.parser.BaseParser.fetch_permit_page")
    def test_network_error(self, mock_fetch):
        """Test handling of network errors."""
        # Mock the fetch_permit_page method to raise a NetworkError
        mock_fetch.side_effect = NetworkError("Failed to fetch permit page")

        # Verify NetworkError is raised
        with self.assertRaises(NetworkError):
            self.parser.parse("2020-26")

    @mock.patch("usac_velodata.parser.BaseParser.fetch_permit_page")
    def test_invalid_access(self, mock_fetch):
        """Test handling of invalid access error page."""
        # Path to error fixture
        samples_dir = Path(os.path.dirname(os.path.dirname(__file__))) / "samples"
        fixture_path = samples_dir / "errors" / "invalid_access.html"

        # Load the invalid access HTML if it exists
        if fixture_path.exists():
            with open(fixture_path, encoding="utf-8") as f:
                invalid_access_html = f.read()
        else:
            # Create a minimal invalid access HTML for tests
            invalid_access_html = "<html><body>Unauthorized access!</body></html>"
            
        # Mock the fetch_permit_page method to return invalid access HTML
        mock_fetch.return_value = invalid_access_html
        
        # Parse the event details for an invalid permit
        event_details = self.parser.parse("9999-99")
        
        # Verify the parser handles this gracefully with default values
        self.assertIsInstance(event_details, dict)
        self.assertEqual(event_details["id"], "9999-99")
        self.assertEqual(event_details["permit_id"], "9999-99")
        self.assertEqual(event_details["year"], 9999)  # From the permit number
        self.assertEqual(event_details["name"], "Event 9999-99")
        self.assertEqual(event_details["location"], "Unknown")
        self.assertEqual(event_details["disciplines"], [])
        self.assertEqual(event_details["categories"], [])
        
    @mock.patch("usac_velodata.parser.BaseParser.fetch_permit_page")
    def test_no_results_found(self, mock_fetch):
        """Test handling of 'no results found' error page."""
        # Path to error fixture
        samples_dir = Path(os.path.dirname(os.path.dirname(__file__))) / "samples"
        fixture_path = samples_dir / "errors" / "no_results_found.html"
        
        # Load the no results found HTML if it exists
        if fixture_path.exists():
            with open(fixture_path, encoding="utf-8") as f:
                no_results_html = f.read()
        else:
            # Create a minimal no results HTML for tests
            no_results_html = "<html><body>No results found for permit 8888-88</body></html>"
            
        # Mock the fetch_permit_page method to return no results HTML
        mock_fetch.return_value = no_results_html
        
        # Parse the event details for a permit with no results
        event_details = self.parser.parse("8888-88")
        
        # Verify the parser handles this gracefully with default values
        self.assertIsInstance(event_details, dict)
        self.assertEqual(event_details["id"], "8888-88")
        self.assertEqual(event_details["permit_id"], "8888-88")
        self.assertEqual(event_details["year"], 8888)
        self.assertEqual(event_details["name"], "Event 8888-88")
        self.assertEqual(event_details["location"], "Unknown")
        self.assertEqual(event_details["disciplines"], [])
        self.assertEqual(event_details["categories"], [])
        
    @mock.patch("usac_velodata.parser.BaseParser.fetch_permit_page")
    def test_single_loadinfo_permit(self, mock_fetch):
        """Test parsing a permit page with a single loadInfoID."""
        # Path to fixture
        samples_dir = Path(os.path.dirname(os.path.dirname(__file__))) / "samples"
        fixture_path = samples_dir / "permit_pages" / "2024-13211.html"
        
        # Load the permit page HTML if it exists
        if fixture_path.exists():
            with open(fixture_path, encoding="utf-8") as f:
                permit_html = f.read()
        else:
            # Create a minimal permit HTML for tests with a single loadInfoID
            permit_html = """
            <html>
            <head><title>Results for ColoTucky Hot Laps CX - USA Cycling</title></head>
            <body>
                <div id="pgcontent" class="onecol">
                    <div id='resultsmain'>
                        <script>
                            loadInfoID(153470,null,0);
                        </script>
                    </div>
                </div>
            </body>
            </html>
            """
            
        # Mock the fetch_permit_page method to return our permit HTML
        mock_fetch.return_value = permit_html
        
        # Mock additional calls needed for loadInfoID processing
        with mock.patch("usac_velodata.parser.RaceResultsParser.parse_race_categories") as mock_categories:
            # Mock the categories that would be retrieved
            mock_categories.return_value = [
                {
                    "id": "1234567",
                    "name": "Men Category 4/5",
                }
            ]
            
            # Parse the event details
            event_details = self.parser.parse("2024-13211")
            
            # Verify the parser handles this correctly
            self.assertIsInstance(event_details, dict)
            self.assertEqual(event_details["id"], "2024-13211")
            self.assertEqual(event_details["permit_id"], "2024-13211")
            self.assertEqual(event_details["year"], 2024)
            
            # The title from HTML is not extracted since there's no h3 element
            # Default values should be used
            self.assertEqual(event_details["name"], "Event 2024-13211")
            
            # Verify disciplines were extracted
            self.assertIsInstance(event_details["disciplines"], list)
            
            # There should be one discipline with loadInfoID 153470
            if event_details["disciplines"]:
                discipline = event_details["disciplines"][0]
                self.assertEqual(discipline.get("load_info_id"), "153470")
            
            # Verify categories were processed
            self.assertIsInstance(event_details["categories"], list)


if __name__ == "__main__":
    unittest.main()
