"""Tests for the flyer fetcher functionality."""

import gzip
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

import requests

from usac_velodata.parser import FlyerFetcher


class TestFlyerFetcher(unittest.TestCase):
    """Test the FlyerFetcher class."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for testing
        self.temp_dir = tempfile.mkdtemp()

        # Create a virtual mock for boto3
        boto3_mock = mock.MagicMock()
        sys.modules["boto3"] = boto3_mock

        # Create a test instance of FlyerFetcher
        self.fetcher = FlyerFetcher(
            cache_enabled=False,
            rate_limit=False,
            storage_dir=self.temp_dir,
            use_s3=False,
        )

        # Mock the _check_flyer_exists method to always return False
        # This ensures the fetch_flyer test doesn't short-circuit
        self.fetcher._check_flyer_exists = mock.MagicMock(return_value=False)

        # Sample data
        self.permit = "2020-123"
        self.sample_pdf = b"%PDF-1.5\nSample PDF content"
        self.sample_doc = b"Sample DOC content"
        self.sample_docx = b"Sample DOCX content"
        self.sample_html = b"<html><body><table><tr><td>Sample HTML content</td></tr></table></body></html>"

    def tearDown(self):
        """Clean up after the tests."""
        # Remove boto3 mock
        if "boto3" in sys.modules:
            del sys.modules["boto3"]

        # Clean up the temporary directory
        shutil.rmtree(self.temp_dir)

    def test_build_urls(self):
        """Test building flyer URLs."""
        flyer_url = self.fetcher._build_flyer_url(self.permit)
        fallback_url = self.fetcher._build_fallback_flyer_url(self.permit)

        self.assertEqual(flyer_url, f"{self.fetcher.FLYER_URL}?permit={self.permit}")
        self.assertEqual(fallback_url, f"{self.fetcher.FALLBACK_URL}?permit={self.permit}")

    def test_get_filename(self):
        """Test getting filenames."""
        # Test basic filename
        filename = self.fetcher._get_filename(self.permit, ".pdf")
        self.assertEqual(filename, "2020_123.pdf")

        # Test with source
        filename = self.fetcher._get_filename(self.permit, ".html", "std")
        self.assertEqual(filename, "2020_123_std.html")

    def test_get_storage_path(self):
        """Test getting storage paths."""
        filename = "2020_123.pdf"

        # Test local storage
        path = self.fetcher._get_storage_path(filename)
        self.assertEqual(path, os.path.join(self.temp_dir, filename))

        # Test S3 storage
        self.fetcher.use_s3 = True
        path = self.fetcher._get_storage_path(filename)
        self.assertEqual(path, f"{self.fetcher.s3_prefix}/{filename}")

        # Reset for other tests
        self.fetcher.use_s3 = False

    def test_save_flyer_local(self):
        """Test saving a flyer locally."""
        content = b"Test flyer content"
        filename = "test.pdf"

        # Save the flyer
        success = self.fetcher._save_flyer(content, filename)
        self.assertTrue(success)

        # Check if the file exists
        expected_path = os.path.join(self.temp_dir, f"{filename}.gz")
        self.assertTrue(os.path.exists(expected_path))

        # Check the content
        with gzip.open(expected_path, "rb") as f:
            saved_content = f.read()
        self.assertEqual(saved_content, content)

    @mock.patch("src.usac_velodata.parser.FlyerFetcher._get_s3_client")
    @mock.patch("gzip.GzipFile")
    @mock.patch("io.BytesIO")
    def test_save_flyer_s3(self, mock_bytesio, mock_gzipfile, mock_get_s3_client):
        """Test saving a flyer to S3."""
        # Set up boto3 mock
        mock_s3_client = mock.MagicMock()
        mock_get_s3_client.return_value = mock_s3_client

        # Set up BytesIO mock
        mock_bytesio_instance = mock.MagicMock()
        mock_bytesio.return_value = mock_bytesio_instance

        # Set up GzipFile mock
        mock_gzip_context = mock.MagicMock()
        mock_gzipfile.return_value.__enter__.return_value = mock_gzip_context

        # Override any previous mocks

        self.fetcher._get_s3_client = mock_get_s3_client

        # Configure fetcher for S3
        self.fetcher.use_s3 = True
        self.fetcher.s3_bucket = "test-bucket"

        # Save the flyer
        content = b"Test flyer content"
        filename = "test.pdf"
        success = self.fetcher._save_flyer(content, filename)

        # Verify successful operation and S3 client call
        self.assertTrue(success)
        mock_get_s3_client.assert_called_once()
        mock_s3_client.upload_fileobj.assert_called_once()

        # Verify the correct parameters were passed to upload_fileobj
        call_args = mock_s3_client.upload_fileobj.call_args[0]
        self.assertEqual(call_args[0], mock_bytesio_instance)  # File object
        self.assertEqual(call_args[1], "test-bucket")  # Bucket name

    def test_inspect_html(self):
        """Test inspecting HTML content."""
        # Test standard HTML with table
        html_content = b"<html><body>Become an Official<table><tr><td>Sample content</td></tr></table></body></html>"
        source, content = self.fetcher._inspect_html(html_content)
        self.assertEqual(source, "std")
        self.assertTrue(b"<table>" in content)

        # Test custom HTML
        html_content = b"<html><body><div>Custom HTML content</div></body></html>"
        source, content = self.fetcher._inspect_html(html_content)
        self.assertEqual(source, "custom")
        self.assertTrue(b"<div>" in content)

        # Test invalid HTML - this shouldn't raise an exception in the current implementation
        # but should still return a valid response
        source, content = self.fetcher._inspect_html(b"Not HTML content")
        self.assertEqual(source, "custom")

    @mock.patch("usac_velodata.parser.FlyerFetcher._fetch_with_retries")
    def test_fetch_flyer_pdf(self, mock_fetch):
        """Test fetching a PDF flyer."""
        # Mock response
        mock_response = mock.MagicMock()
        mock_response.headers = {"Content-Type": "application/pdf"}
        mock_response.content = self.sample_pdf
        mock_fetch.return_value = mock_response

        # Fetch the flyer
        result = self.fetcher.fetch_flyer(self.permit)

        # Verify result
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["permit"], self.permit)
        self.assertEqual(result["extension"], ".pdf")

        # Verify file was created
        expected_path = os.path.join(self.temp_dir, "2020_123.pdf.gz")
        self.assertTrue(os.path.exists(expected_path))

        # Verify content
        with gzip.open(expected_path, "rb") as f:
            saved_content = f.read()
        self.assertEqual(saved_content, self.sample_pdf)

    @mock.patch("usac_velodata.parser.FlyerFetcher._fetch_with_retries")
    def test_fetch_flyer_html(self, mock_fetch):
        """Test fetching an HTML flyer."""
        # Mock responses
        main_response = mock.MagicMock()
        main_response.headers = {"Content-Type": "text/html"}
        main_response.content = (
            b"<html><body>Become an Official<table><tr><td>Sample content</td></tr></table></body></html>"
        )

        fallback_response = mock.MagicMock()
        fallback_response.headers = {"Content-Type": "text/html"}
        fallback_response.content = (
            b"<html><body>Become an Official<table><tr><td>Sample content</td></tr></table></body></html>"
        )

        # Configure mock to return different responses for different URLs
        def side_effect(url, **kwargs):
            if "getflyer.php" in url:
                return main_response
            else:
                return fallback_response

        mock_fetch.side_effect = side_effect

        # Fetch the flyer
        result = self.fetcher.fetch_flyer(self.permit)

        # Verify result
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["permit"], self.permit)
        self.assertEqual(result["extension"], ".html")
        self.assertEqual(result["source"], "std")

        # Verify file was created
        expected_path = os.path.join(self.temp_dir, "2020_123_std.html.gz")
        self.assertTrue(os.path.exists(expected_path))

    @mock.patch("usac_velodata.parser.FlyerFetcher._fetch_with_retries")
    def test_fetch_flyer_error(self, mock_fetch):
        """Test fetching a flyer with an error."""
        # Mock fetch to raise an exception
        mock_fetch.side_effect = requests.RequestException("Test error")

        # Fetch the flyer
        result = self.fetcher.fetch_flyer(self.permit)

        # Verify result
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["permit"], self.permit)
        self.assertIn("error", result)

    @mock.patch("usac_velodata.parser.FlyerFetcher.fetch_flyer")
    @mock.patch("time.sleep")
    def test_fetch_flyers_batch(self, mock_sleep, mock_fetch_flyer):
        """Test fetching multiple flyers in a batch."""
        # Mock fetch_flyer to return different results
        results = [
            {"status": "success", "permit": "2020-1"},
            {"status": "exists", "permit": "2020-2"},
            {"status": "error", "permit": "2020-3", "error": "Test error"},
        ]
        mock_fetch_flyer.side_effect = results

        # Mock client
        with mock.patch("usac_velodata.client.USACyclingClient") as mock_client:
            # Configure mock client to return events
            mock_instance = mock_client.return_value
            mock_instance.get_events.return_value = [
                mock.MagicMock(permit_id="2020-1"),
                mock.MagicMock(permit_id="2020-2"),
                mock.MagicMock(permit_id="2020-3"),
            ]

            # Fetch flyers
            result = self.fetcher.fetch_flyers_batch(2020, 2020, limit=3, delay=0)

            # Verify result
            self.assertEqual(result["total_processed"], 3)
            self.assertEqual(result["fetched"], 1)
            self.assertEqual(result["existing"], 1)
            self.assertEqual(result["errors"], 1)

    def test_list_flyers(self):
        """Test listing flyers."""
        # Create test files
        files = [
            "2020_123.pdf.gz",
            "2020_456_std.html.gz",
            "2021_789.docx.gz",
        ]
        for file in files:
            with open(os.path.join(self.temp_dir, file), "w") as f:
                f.write("test")

        # List flyers
        flyers = self.fetcher.list_flyers()

        # Verify results
        self.assertEqual(len(flyers), 3)
        filenames = [f["filename"] for f in flyers]
        self.assertIn("2020_123.pdf", filenames)
        self.assertIn("2020_456_std.html", filenames)
        self.assertIn("2021_789.docx", filenames)

        # Verify storage type
        self.assertEqual(flyers[0]["storage"], "local")


if __name__ == "__main__":
    unittest.main()
