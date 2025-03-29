"""Tests for the USACyclingClient class."""

import os
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

from src.usac_velodata import USACyclingClient
from src.usac_velodata.exceptions import ValidationError
from src.usac_velodata.models import Event, EventDetails, RaceCategory, RaceResult


class TestUSACyclingClient(unittest.TestCase):
    """Tests for the USACyclingClient class."""

    def setUp(self):
        """Set up test environment."""
        self.client = USACyclingClient(cache_enabled=False)

        # Path to test fixtures
        self.samples_dir = Path(os.path.dirname(os.path.dirname(__file__))) / "samples"

    @mock.patch("src.usac_velodata.parser.EventListParser.get_events")
    def test_get_events(self, mock_get_events):
        """Test getting events."""
        # Mock the parser's get_events method
        mock_get_events.return_value = [
            {
                "id": "2020-26",
                "name": "USA Cycling December VRL",
                "permit": "2020-26",
                "event_date": date(2020, 12, 2),
                "location": "Colorado Springs",
                "submit_date": date(2020, 12, 18),
                "permit_url": "https://legacy.usacycling.org/results/?permit=2020-26",
                "year": 2020,
                "state": "CO",
            }
        ]

        # Get events
        events = self.client.get_events("CO", 2020)

        # Verify results
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], Event)
        self.assertEqual(events[0].id, "2020-26")
        self.assertEqual(events[0].name, "USA Cycling December VRL")
        self.assertEqual(events[0].state, "CO")
        self.assertEqual(events[0].year, 2020)

    def test_get_events_invalid_state(self):
        """Test getting events with an invalid state."""
        with self.assertRaises(ValidationError):
            self.client.get_events("", 2020)

        with self.assertRaises(ValidationError):
            self.client.get_events("USA", 2020)

    @mock.patch("src.usac_velodata.parser.EventDetailsParser.get_event_details")
    def test_get_event_details(self, mock_get_event_details):
        """Test getting event details."""
        # Mock the parser's get_event_details method
        mock_get_event_details.return_value = {
            "id": "2020-26",
            "name": "USA Cycling December VRL",
            "permit_number": "2020-26",
            "start_date": date(2020, 12, 2),
            "end_date": date(2020, 12, 30),
            "location": "Colorado Springs",
            "state": "CO",
            "year": 2020,
            "disciplines": [],
            "categories": [],
            "is_usac_sanctioned": True,
            "promoter": None,
            "promoter_email": None,
            "website": None,
            "registration_url": None,
            "description": None,
            "dates": []
        }

        # Get event details
        event_details = self.client.get_event_details("2020-26")

        # Verify results
        self.assertIsInstance(event_details, EventDetails)
        self.assertEqual(event_details.id, "2020-26")
        self.assertEqual(event_details.name, "USA Cycling December VRL")
        self.assertEqual(event_details.state, "CO")
        self.assertEqual(event_details.year, 2020)
        self.assertEqual(event_details.disciplines, [])

    @mock.patch("src.usac_velodata.parser.RaceResultsParser.parse_race_categories")
    def test_get_race_categories(self, mock_parse_race_categories):
        """Test getting race categories."""
        # Mock the parser's parse_race_categories method
        mock_parse_race_categories.return_value = [
            {
                "id": "1337864",
                "name": "XCU Men 1:55 Category A",
                "info_id": "132893",
                "label": "Cross Country Ultra Endurance 12/02/2020",
                "discipline": "Cross Country Ultra Endurance",
                "gender": "Men",
                "category_type": None,
                "age_range": None,
                "category_rank": "A",
                "event_name": "USA Cycling December VRL",
                "event_location": "Colorado Springs, CO",
                "event_date_range": "Dec 2, 2020 - Dec 30, 2020",
            }
        ]

        # Get race categories
        categories = self.client.get_race_categories("132893", "Cross Country Ultra Endurance 12/02/2020")

        # Verify results
        self.assertEqual(len(categories), 1)
        self.assertIsInstance(categories[0], RaceCategory)
        self.assertEqual(categories[0].id, "1337864")
        self.assertEqual(categories[0].name, "XCU Men 1:55 Category A")
        self.assertEqual(categories[0].gender, "Men")
        self.assertEqual(categories[0].category_rank, "A")

    @mock.patch("src.usac_velodata.parser.RaceResultsParser.get_race_results")
    def test_get_race_results(self, mock_get_race_results):
        """Test getting race results."""
        # Mock the parser's get_race_results method
        mock_get_race_results.return_value = {
            "id": "1337864",
            "category": {"id": "1337864", "name": "XCU Men 1:55 Category A", "event_id": "2020-26"},
            "riders": [
                {
                    "place": "1",
                    "place_number": 1,
                    "name": "John Doe",
                    "city": "Colorado Springs",
                    "state": "CO",
                    "team": "Team A",
                    "license": "12345",
                    "bib": "101",
                    "time": "1:30:00",
                    "is_dnf": False,
                    "is_dns": False,
                    "is_dq": False,
                }
            ],
            "event_id": "2020-26",
            "date": date(2020, 12, 2),
        }

        # Get race results
        race_results = self.client.get_race_results("1337864")

        # Verify results
        self.assertIsInstance(race_results, RaceResult)
        self.assertEqual(race_results.id, "1337864")
        self.assertEqual(race_results.event_id, "2020-26")
        self.assertEqual(len(race_results.riders), 1)
        self.assertEqual(race_results.riders[0].name, "John Doe")
        self.assertEqual(race_results.riders[0].place, "1")

    @mock.patch("src.usac_velodata.parser.EventDetailsParser.fetch_permit_page")
    def test_get_disciplines_for_event(
        self, mock_fetch_permit_page
    ):
        """Test getting disciplines for an event."""
        # Mock fetch_permit_page
        # Load sample data from file
        with open("samples/permit_pages/2020-26.html", "r") as f:
            mock_fetch_permit_page.return_value = f.read()

        # Get disciplines
        disciplines = self.client.get_disciplines_for_event("2020-26")

        # Verify results
        self.assertEqual(len(disciplines), 5)
        self.assertEqual(disciplines[0]["id"], "132893")
        self.assertEqual(disciplines[0]["name"], "Cross Country Ultra Endurance")
        self.assertEqual(disciplines[0]["label"], "Cross Country Ultra Endurance 12/02/2020")
        self.assertEqual(disciplines[1]["id"], "132897")
        self.assertEqual(disciplines[1]["name"], "Cross Country Ultra Endurance")
        self.assertEqual(disciplines[1]["label"], "Cross Country Ultra Endurance 12/09/2020")


    @mock.patch("src.usac_velodata.client.USACyclingClient.get_event_details")
    @mock.patch("src.usac_velodata.client.USACyclingClient.get_disciplines_for_event")
    @mock.patch("src.usac_velodata.client.USACyclingClient.get_race_categories")
    @mock.patch("src.usac_velodata.client.USACyclingClient.get_race_results")
    def test_get_complete_event_data(
        self, mock_get_race_results, mock_get_race_categories, mock_get_disciplines, mock_get_event_details
    ):
        """Test getting complete event data."""
        # Mock get_event_details
        event_details = mock.MagicMock(spec=EventDetails)
        event_details.id = "2020-26"
        event_details.name = "USA Cycling December VRL"
        mock_get_event_details.return_value = event_details

        # Mock get_disciplines_for_event
        mock_get_disciplines.return_value = [
            {
                "id": "132893",
                "name": "Cross Country Ultra Endurance",
                "label": "Cross Country Ultra Endurance 12/02/2020",
            }
        ]

        # Mock get_race_categories
        category = mock.MagicMock(spec=RaceCategory)
        category.id = "1337864"
        category.name = "XCU Men 1:55 Category A"
        category.event_id = "2020-26"
        category.discipline = "Cross Country Ultra Endurance"
        category.gender = "Men"
        category.category_type = None
        category.age_range = None
        category.category_rank = "A"
        mock_get_race_categories.return_value = [category]

        # Mock get_race_results
        race_result = mock.MagicMock(spec=RaceResult)
        race_result.id = "1337864"
        race_result.event_id = "2020-26"
        mock_get_race_results.return_value = race_result

        # Get complete event data
        event_data = self.client.get_complete_event_data("2020-26")

        # Verify results
        self.assertEqual(event_data["event"], event_details)
        self.assertEqual(len(event_data["disciplines"]), 1)
        self.assertEqual(event_data["disciplines"][0]["id"], "132893")
        self.assertEqual(len(event_data["categories"]), 1)
        self.assertEqual(event_data["categories"][0], category)
        self.assertEqual(len(event_data["results"]), 1)
        self.assertEqual(event_data["results"]["1337864"], race_result)

    def test_parse_date(self):
        """Test parsing a date string."""
        # Test with various date formats
        self.assertEqual(self.client._parse_date("12/31/2020"), date(2020, 12, 31))
        self.assertEqual(self.client._parse_date("2020-12-31"), date(2020, 12, 31))
        self.assertEqual(self.client._parse_date("December 31, 2020"), date(2020, 12, 31))
        self.assertEqual(self.client._parse_date("Dec 31, 2020"), date(2020, 12, 31))

        # Test with invalid date format
        today = date.today()
        self.assertEqual(self.client._parse_date("Invalid date"), today)

    @mock.patch("src.usac_velodata.client.FlyerFetcher")
    def test_fetch_flyer(self, mock_flyer_fetcher_class):
        """Test the fetch_flyer method."""
        # Set up mock
        mock_fetcher = mock.MagicMock()
        mock_flyer_fetcher_class.return_value = mock_fetcher
        mock_fetcher.fetch_flyer.return_value = {
            "status": "success",
            "permit": "2020-123",
            "filename": "2020_123.pdf",
        }

        # Call the method
        result = self.client.fetch_flyer(
            permit="2020-123",
            storage_dir="./test_flyers",
            use_s3=False,
        )

        # Verify the result
        self.assertEqual(result["status"], "success")
        
        # Verify that FlyerFetcher was initialized correctly
        mock_flyer_fetcher_class.assert_called_once()
        call_kwargs = mock_flyer_fetcher_class.call_args[1]
        self.assertEqual(call_kwargs["storage_dir"], "./test_flyers")
        self.assertEqual(call_kwargs["use_s3"], False)
        
        # Verify that fetch_flyer was called with correct args
        mock_fetcher.fetch_flyer.assert_called_once_with("2020-123")

    @mock.patch("src.usac_velodata.client.FlyerFetcher")
    def test_fetch_flyers_batch(self, mock_flyer_fetcher_class):
        """Test the fetch_flyers_batch method."""
        # Set up mock
        mock_fetcher = mock.MagicMock()
        mock_flyer_fetcher_class.return_value = mock_fetcher
        mock_fetcher.fetch_flyers_batch.return_value = {
            "total_processed": 3,
            "fetched": 2,
            "existing": 1,
            "errors": 0,
        }

        # Call the method
        result = self.client.fetch_flyers_batch(
            start_year=2020,
            end_year=2021,
            limit=10,
            delay=5,
            storage_dir="./test_flyers",
            use_s3=False,
        )

        # Verify the result
        self.assertEqual(result["total_processed"], 3)
        
        # Verify that FlyerFetcher was initialized correctly
        mock_flyer_fetcher_class.assert_called_once()
        call_kwargs = mock_flyer_fetcher_class.call_args[1]
        self.assertEqual(call_kwargs["storage_dir"], "./test_flyers")
        self.assertEqual(call_kwargs["use_s3"], False)
        
        # Verify that fetch_flyers_batch was called with correct args
        mock_fetcher.fetch_flyers_batch.assert_called_once()
        call_args = mock_fetcher.fetch_flyers_batch.call_args[1]
        self.assertEqual(call_args["start_year"], 2020)
        self.assertEqual(call_args["end_year"], 2021)
        self.assertEqual(call_args["limit"], 10)
        self.assertEqual(call_args["delay"], 5)

    @mock.patch("src.usac_velodata.client.FlyerFetcher")
    def test_list_flyers(self, mock_flyer_fetcher_class):
        """Test the list_flyers method."""
        # Set up mock
        mock_fetcher = mock.MagicMock()
        mock_flyer_fetcher_class.return_value = mock_fetcher
        mock_fetcher.list_flyers.return_value = [
            {
                "filename": "2020_123.pdf",
                "size": 1024,
                "last_modified": "2023-01-01T00:00:00",
                "storage": "local",
                "path": "./test_flyers/2020_123.pdf.gz"
            }
        ]

        # Call the method
        result = self.client.list_flyers(
            storage_dir="./test_flyers",
            use_s3=False,
        )

        # Verify the result
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["filename"], "2020_123.pdf")
        
        # Verify that FlyerFetcher was initialized correctly
        mock_flyer_fetcher_class.assert_called_once()
        call_kwargs = mock_flyer_fetcher_class.call_args[1]
        self.assertEqual(call_kwargs["storage_dir"], "./test_flyers")
        self.assertEqual(call_kwargs["use_s3"], False)
        
        # Verify that list_flyers was called
        mock_fetcher.list_flyers.assert_called_once()


if __name__ == "__main__":
    unittest.main()
