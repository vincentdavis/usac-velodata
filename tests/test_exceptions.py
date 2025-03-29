"""Tests for the custom exception classes."""

from usac_velodata.exceptions import (
    CacheError,
    ConfigurationError,
    NetworkError,
    ParseError,
    RateLimitError,
    USACyclingError,
    ValidationError,
)


def test_base_exception():
    """Test the base USACyclingError class."""
    # Basic exception with message only
    error = USACyclingError("Test error")
    assert str(error) == "Test error"
    assert error.message == "Test error"
    assert error.cause is None
    assert error.details == {}

    # Exception with cause
    cause = ValueError("Original error")
    error = USACyclingError("Test error", cause=cause)
    assert "Test error Caused by: Original error" in str(error)
    assert error.cause == cause

    # Exception with details
    error = USACyclingError("Test error", details={"key": "value"})
    assert error.details == {"key": "value"}


def test_network_error():
    """Test the NetworkError class."""
    # Basic NetworkError
    error = NetworkError("Network error")
    assert str(error) == "Network error"
    assert error.url is None
    assert error.status_code is None

    # NetworkError with URL and status code
    error = NetworkError("Network error", url="https://example.com", status_code=404)
    assert error.url == "https://example.com"
    assert error.status_code == 404
    assert error.details == {"url": "https://example.com", "status_code": 404}

    # NetworkError with cause
    cause = ConnectionError("Failed to connect")
    error = NetworkError("Network error", cause=cause)
    assert "Network error Caused by: Failed to connect" in str(error)
    assert error.cause == cause


def test_parse_error():
    """Test the ParseError class."""
    # Basic ParseError
    error = ParseError("Parse error")
    assert str(error) == "Parse error"
    assert error.source is None
    assert error.selector is None

    # ParseError with source and selector
    error = ParseError("Parse error", source="Event page", selector=".results-table")
    assert error.source == "Event page"
    assert error.selector == ".results-table"
    assert error.details == {"source": "Event page", "selector": ".results-table"}


def test_validation_error():
    """Test the ValidationError class."""
    # Basic ValidationError
    error = ValidationError("Validation error")
    assert str(error) == "Validation error"
    assert error.field is None
    assert error.value is None

    # ValidationError with field and value
    error = ValidationError("Validation error", field="date", value="not-a-date")
    assert error.field == "date"
    assert error.value == "not-a-date"
    assert error.details == {"field": "date", "value": "not-a-date"}

    # ValidationError with falsey value
    error = ValidationError("Validation error", field="active", value=False)
    assert error.value is False
    assert error.details == {"field": "active", "value": False}


def test_rate_limit_error():
    """Test the RateLimitError class."""
    # Basic RateLimitError
    error = RateLimitError("Rate limit exceeded")
    assert str(error) == "Rate limit exceeded"
    assert error.url is None
    assert error.retry_after is None

    # RateLimitError with URL and retry_after
    error = RateLimitError("Rate limit exceeded", url="https://example.com", retry_after=60)
    assert error.url == "https://example.com"
    assert error.retry_after == 60
    assert error.details == {"url": "https://example.com", "retry_after": 60}


def test_cache_error():
    """Test the CacheError class."""
    # Basic CacheError
    error = CacheError("Cache error")
    assert str(error) == "Cache error"
    assert error.cache_key is None
    assert error.operation is None

    # CacheError with cache_key and operation
    error = CacheError("Cache error", cache_key="events:CA:2023", operation="write")
    assert error.cache_key == "events:CA:2023"
    assert error.operation == "write"
    assert error.details == {"cache_key": "events:CA:2023", "operation": "write"}


def test_configuration_error():
    """Test the ConfigurationError class."""
    # Basic ConfigurationError
    error = ConfigurationError("Configuration error")
    assert str(error) == "Configuration error"
    assert error.parameter is None
    assert error.value is None

    # ConfigurationError with parameter and value
    error = ConfigurationError("Configuration error", parameter="rate_limit", value=-1)
    assert error.parameter == "rate_limit"
    assert error.value == -1
    assert error.details == {"parameter": "rate_limit", "value": -1}


def test_exception_hierarchy():
    """Test that all exceptions inherit from USACyclingError."""
    assert issubclass(NetworkError, USACyclingError)
    assert issubclass(ParseError, USACyclingError)
    assert issubclass(ValidationError, USACyclingError)
    assert issubclass(RateLimitError, USACyclingError)
    assert issubclass(CacheError, USACyclingError)
    assert issubclass(ConfigurationError, USACyclingError)

    # Test that exceptions can be caught by catching USACyclingError
    try:
        raise NetworkError("Network error")
    except USACyclingError as e:
        assert isinstance(e, NetworkError)
