"""Tests for the BaseParser class."""

import tempfile
import unittest
from unittest import mock

import requests
from bs4 import BeautifulSoup

from usac_velodata.exceptions import NetworkError, ParseError
from usac_velodata.parser import BaseParser


class TestBaseParser(unittest.TestCase):
    """Tests for the BaseParser class."""

    def setUp(self):
        """Set up test environment."""
        # Create a temporary directory for cache
        self.temp_dir = tempfile.TemporaryDirectory()
        self.cache_dir = self.temp_dir.name

        # Create a parser with caching enabled
        self.parser = BaseParser(cache_enabled=True, cache_dir=self.cache_dir, max_retries=2, retry_delay=0.1)

        # Sample URLs for testing
        self.event_list_url = f"{self.parser.BASE_URL}/results/browse.php"
        self.permit_url = f"{self.parser.RESULTS_URL}?permit=2020-26"

        # Breaking long URLs into parts
        base_api = self.parser.API_URL
        self.load_info_url = f"{base_api}?ajax=1&act=infoid&info_id=132893&label=Test"
        self.race_results_url = f"{base_api}?ajax=1&act=loadresults&race_id=1337864"

    def tearDown(self):
        """Clean up after tests."""
        self.temp_dir.cleanup()

    @mock.patch("requests.Session.request")
    def test_fetch_content(self, mock_request):
        """Test fetching HTML content."""
        # Mock response
        mock_response = mock.Mock()
        mock_response.text = "<html><body>Test content</body></html>"
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        # Fetch content
        content = self.parser._fetch_content(self.event_list_url)
        # Verify
        self.assertEqual(content, "<html><body>Test content</body></html>")
        mock_request.assert_called_once()

    @mock.patch("requests.Session.request")
    def test_fetch_content_with_cache(self, mock_request):
        """Test fetching HTML content with caching."""
        # Mock response
        mock_response = mock.Mock()
        mock_response.text = "<html><body>Test content</body></html>"
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        # Create a subclass with overridden cache methods for testing
        class TestParser(BaseParser):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.cache_data = None

            def _get_from_cache(self, url):
                return self.cache_data

            def _save_to_cache(self, url, data, expire_seconds=3600):
                self.cache_data = {"response": data}

        # Use our test parser
        test_parser = TestParser(cache_enabled=True, cache_dir=self.cache_dir, max_retries=2, retry_delay=0.1)

        # First request should use the network
        content1 = test_parser._fetch_content(self.event_list_url)

        # Second request should use cache
        content2 = test_parser._fetch_content(self.event_list_url)

        # Verify contents match and network only called once
        self.assertEqual(content1, content2)
        mock_request.assert_called_once()

    @mock.patch("requests.Session.request")
    def test_fetch_content_network_error(self, mock_request):
        """Test handling network errors."""
        # Mock connection error
        error_msg = "Connection failed"
        mock_request.side_effect = requests.exceptions.ConnectionError(error_msg)

        # Verify NetworkError is raised
        with self.assertRaises(NetworkError):
            self.parser._fetch_content(self.event_list_url)

    @mock.patch("requests.Session.request")
    def test_fetch_json(self, mock_request):
        """Test fetching JSON data."""
        # Mock response
        mock_response = mock.Mock()
        mock_response.json.return_value = {"data": "test"}
        mock_response.text = '{"data": "test"}'
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        # Fetch JSON
        data = self.parser._fetch_json(self.load_info_url)

        # Verify
        self.assertEqual(data, {"data": "test"})
        mock_request.assert_called_once()

    @mock.patch("requests.Session.request")
    def test_fetch_json_parse_error(self, mock_request):
        """Test handling JSON parsing errors."""
        # Mock invalid JSON
        mock_response = mock.Mock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.text = "<html>Not JSON</html>"
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        # Verify ParseError is raised
        with self.assertRaises(ParseError):
            self.parser._fetch_json(self.load_info_url)

    def test_make_soup(self):
        """Test creating a BeautifulSoup object."""
        html = "<html><body>Test</body></html>"
        soup = self.parser._make_soup(html)

        self.assertIsInstance(soup, BeautifulSoup)
        # Use find method instead of direct attribute access
        body = soup.find("body")
        self.assertIsNotNone(body)
        self.assertEqual(body.get_text(), "Test")

    def test_extract_text(self):
        """Test extracting text from BeautifulSoup elements."""
        html = "<div>   Test text with spaces   </div>"
        soup = self.parser._make_soup(html)

        # Extract text from element
        text = self.parser._extract_text(soup.div)

        # Verify
        self.assertEqual(text, "Test text with spaces")

        # Test with None
        self.assertEqual(self.parser._extract_text(None), "")

    def test_extract_date(self):
        """Test extracting dates from strings."""
        # Test various date formats
        date1 = self.parser._extract_date("12/31/2020")
        date2 = self.parser._extract_date("2020-12-31")
        date3 = self.parser._extract_date("December 31, 2020")
        date4 = self.parser._extract_date("Invalid date")

        # Verify
        self.assertEqual(str(date1), "2020-12-31")
        self.assertEqual(str(date2), "2020-12-31")
        self.assertEqual(str(date3), "2020-12-31")
        self.assertIsNone(date4)

    def test_extract_load_info_id(self):
        """Test extracting load info IDs from onclick attributes."""
        onclick = "loadInfoID(123456, 'Test Category')"
        load_info_id = self.parser._extract_load_info_id(onclick)

        self.assertEqual(load_info_id, "123456")

        # Test with invalid onclick
        self.assertIsNone(self.parser._extract_load_info_id("invalid"))
        # Only pass string values, not None
        self.assertIsNone(self.parser._extract_load_info_id(""))

    def test_extract_race_id(self):
        """Test extracting race IDs from element IDs."""
        race_id = self.parser._extract_race_id("race_7890123")

        self.assertEqual(race_id, "7890123")

        # Test with invalid race ID
        self.assertIsNone(self.parser._extract_race_id("invalid"))
        # Only pass string values, not None
        self.assertIsNone(self.parser._extract_race_id(""))

    def test_build_urls(self):
        """Test building URLs for different endpoints."""
        # Test permit URL
        permit_url = self.parser._build_permit_url("2020-26")
        self.assertEqual(permit_url, "https://legacy.usacycling.org/results/?permit=2020-26")

        # Test load info URL
        load_info_url = self.parser._build_load_info_url("123456", "Test Category")
        self.assertTrue("ajax=1" in load_info_url)
        self.assertTrue("act=infoid" in load_info_url)
        self.assertTrue("info_id=123456" in load_info_url)

        # Test race results URL
        race_results_url = self.parser._build_race_results_url("7890123")
        self.assertTrue("ajax=1" in race_results_url)
        self.assertTrue("act=loadresults" in race_results_url)
        self.assertTrue("race_id=7890123" in race_results_url)

    @mock.patch("usac_velodata.parser.BaseParser._fetch_content")
    def test_fetch_event_list(self, mock_fetch):
        """Test fetching event lists."""
        # Mock response
        mock_fetch.return_value = "<html>Event list</html>"

        # Fetch event list
        content = self.parser.fetch_event_list("CA", 2020)

        # Verify
        self.assertEqual(content, "<html>Event list</html>")
        mock_fetch.assert_called_once()

    @mock.patch("usac_velodata.parser.BaseParser._fetch_content")
    def test_fetch_permit_page(self, mock_fetch):
        """Test fetching permit pages."""
        # Mock response
        mock_fetch.return_value = "<html>Permit page</html>"

        # Fetch permit page
        content = self.parser.fetch_permit_page("2020-26")

        # Verify
        self.assertEqual(content, "<html>Permit page</html>")
        mock_fetch.assert_called_once()

    @mock.patch("usac_velodata.parser.BaseParser._fetch_content")
    def test_fetch_load_info(self, mock_fetch):
        """Test fetching load info data."""
        # Mock response
        mock_fetch.return_value = "<html><ul><li id='race_123'><a>Test Race</a></li></ul></html>"

        # Fetch load info
        data = self.parser.fetch_load_info("123456", "Test")

        # Verify
        self.assertIn("categories", data)
        mock_fetch.assert_called_once()

    @mock.patch("usac_velodata.parser.BaseParser._fetch_with_retries")
    def test_fetch_race_results(self, mock_fetch):
        """Test fetching race results data."""
        # Mock response
        mock_response = mock.Mock()
        mock_response.text = "<html><span class='race-name'>Test Race</span><div class='tablerow'></div></html>"
        mock_fetch.return_value = mock_response

        # Fetch race results
        data = self.parser.fetch_race_results("7890123")

        # Verify
        self.assertIn("name", data)
        self.assertIn("riders", data)
        mock_fetch.assert_called_once()


if __name__ == "__main__":
    unittest.main()
