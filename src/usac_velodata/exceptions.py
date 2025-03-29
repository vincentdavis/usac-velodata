"""Custom exceptions for the USA Cycling Results Parser package.

This module defines a hierarchy of exceptions used throughout the package
to handle various error conditions in a structured way.
"""

from typing import Any


class USACyclingError(Exception):
    """Base exception for all USA Cycling parser errors.

    All other exceptions in this package inherit from this base class,
    allowing users to catch all package-specific exceptions with a single
    except clause.
    """

    def __init__(self, message: str, cause: Exception | None = None, details: dict[str, Any] | None = None):
        """Initialize the exception.

        Args:
            message: Human-readable error message
            cause: Original exception that caused this error, if any
            details: Additional details about the error context

        """
        self.message = message
        self.cause = cause
        self.details = details or {}

        # Build the full message
        full_message = message
        if cause:
            full_message += f" Caused by: {cause!s}"

        super().__init__(full_message)


class NetworkError(USACyclingError):
    """Exception raised for network-related errors.

    This includes connection issues, timeouts, and HTTP errors
    when communicating with USA Cycling servers.
    """

    def __init__(
        self,
        message: str,
        url: str | None = None,
        status_code: int | None = None,
        cause: Exception | None = None,
        details: dict[str, Any] | None = None,
    ):
        """Initialize the network error.

        Args:
            message: Human-readable error message
            url: The URL that was being accessed when the error occurred
            status_code: HTTP status code, if applicable
            cause: Original exception that caused this error, if any
            details: Additional details about the error context

        """
        self.url = url
        self.status_code = status_code

        # Add URL and status code to details
        full_details = details or {}
        if url:
            full_details["url"] = url
        if status_code:
            full_details["status_code"] = status_code

        super().__init__(message, cause, full_details)


class ParseError(USACyclingError):
    """Exception raised for parsing errors.

    This occurs when the parser encounters unexpected content structure
    or when extraction of specific data fails.
    """

    def __init__(
        self,
        message: str,
        source: str | None = None,
        selector: str | None = None,
        cause: Exception | None = None,
        details: dict[str, Any] | None = None,
    ):
        """Initialize the parse error.

        Args:
            message: Human-readable error message
            source: Description of the content source being parsed
            selector: The CSS selector or XPath that failed, if applicable
            cause: Original exception that caused this error, if any
            details: Additional details about the error context

        """
        self.source = source
        self.selector = selector

        # Add source and selector to details
        full_details = details or {}
        if source:
            full_details["source"] = source
        if selector:
            full_details["selector"] = selector

        super().__init__(message, cause, full_details)


class ValidationError(USACyclingError):
    """Exception raised for data validation errors.

    This occurs when parsed data doesn't conform to the expected schema
    or contains invalid values.
    """

    def __init__(
        self,
        message: str,
        field: str | None = None,
        value: Any | None = None,
        cause: Exception | None = None,
        details: dict[str, Any] | None = None,
    ):
        """Initialize the validation error.

        Args:
            message: Human-readable error message
            field: The field that failed validation, if applicable
            value: The invalid value, if applicable
            cause: Original exception that caused this error, if any
            details: Additional details about the error context

        """
        self.field = field
        self.value = value

        # Add field and value to details
        full_details = details or {}
        if field:
            full_details["field"] = field
        if value is not None:  # Allow value to be False or 0
            full_details["value"] = value

        super().__init__(message, cause, full_details)


class RateLimitError(USACyclingError):
    """Exception raised when hitting rate limits.

    This occurs when the USA Cycling server rejects requests due to
    exceeding the allowed number of requests in a time period.
    """

    def __init__(
        self,
        message: str,
        url: str | None = None,
        retry_after: int | float | None = None,
        cause: Exception | None = None,
        details: dict[str, Any] | None = None,
    ):
        """Initialize the rate limit error.

        Args:
            message: Human-readable error message
            url: The URL that triggered the rate limit
            retry_after: Suggested seconds to wait before retrying, if available
            cause: Original exception that caused this error, if any
            details: Additional details about the error context

        """
        self.url = url
        self.retry_after = retry_after

        # Add URL and retry_after to details
        full_details = details or {}
        if url:
            full_details["url"] = url
        if retry_after is not None:
            full_details["retry_after"] = retry_after

        super().__init__(message, cause, full_details)


class CacheError(USACyclingError):
    """Exception raised for caching-related errors.

    This occurs when there are issues with storing or retrieving cached data.
    """

    def __init__(
        self,
        message: str,
        cache_key: str | None = None,
        operation: str | None = None,
        cause: Exception | None = None,
        details: dict[str, Any] | None = None,
    ):
        """Initialize the cache error.

        Args:
            message: Human-readable error message
            cache_key: The cache key that was being accessed
            operation: The operation that failed (e.g., "read", "write")
            cause: Original exception that caused this error, if any
            details: Additional details about the error context

        """
        self.cache_key = cache_key
        self.operation = operation

        # Add cache_key and operation to details
        full_details = details or {}
        if cache_key:
            full_details["cache_key"] = cache_key
        if operation:
            full_details["operation"] = operation

        super().__init__(message, cause, full_details)


class ConfigurationError(USACyclingError):
    """Exception raised for configuration-related errors.

    This occurs when the library is configured with invalid parameters
    or incompatible settings.
    """

    def __init__(
        self,
        message: str,
        parameter: str | None = None,
        value: Any | None = None,
        cause: Exception | None = None,
        details: dict[str, Any] | None = None,
    ):
        """Initialize the configuration error.

        Args:
            message: Human-readable error message
            parameter: The configuration parameter that caused the error
            value: The invalid value
            cause: Original exception that caused this error, if any
            details: Additional details about the error context

        """
        self.parameter = parameter
        self.value = value

        # Add parameter and value to details
        full_details = details or {}
        if parameter:
            full_details["parameter"] = parameter
        if value is not None:
            full_details["value"] = value

        super().__init__(message, cause, full_details)
