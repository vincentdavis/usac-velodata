"""Main client interface for the USA Cycling Results Parser package.

This module provides the USACyclingClient class, which serves as the main entry point
for interacting with the USA Cycling results data.
"""

import re
from datetime import date
from typing import Any

from bs4 import BeautifulSoup
from pydantic import ValidationError as pydantic_ValidationError

from .exceptions import NetworkError, ParseError, ValidationError
from .models import Event, EventDetails, RaceCategory, RaceResult, Rider
from .parser import BaseParser, EventDetailsParser, EventListParser, FlyerFetcher, RaceResultsParser
from .utils import configure_logging, logger


class USACyclingClient:
    """Main client interface for the USA Cycling Results Parser.

    This class provides methods to search for events, retrieve event details,
    and access race results from USA Cycling's legacy results website.

    Attributes:
        cache_enabled: Whether to enable response caching
        cache_dir: Directory to store cached responses
        rate_limit: Whether to enable rate limiting

    """

    def __init__(
        self,
        cache_enabled: bool = True,
        cache_dir: str | None = None,
        rate_limit: bool = True,
        max_retries: int = 3,
        retry_delay: float = 2.0,
        log_level: str = "INFO",
    ):
        """Initialize the USA Cycling client.

        Args:
            cache_enabled: Whether to enable response caching
            cache_dir: Directory to store cached responses
            rate_limit: Whether to enable rate limiting
            max_retries: Maximum number of retries for failed requests
            retry_delay: Delay between retries in seconds
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

        """
        self.cache_enabled = cache_enabled
        self.cache_dir = cache_dir
        self.rate_limit = rate_limit
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Configure logging
        configure_logging(level=log_level)

        # Initialize parsers
        self._event_list_parser = EventListParser(
            cache_enabled=cache_enabled,
            cache_dir=cache_dir,
            rate_limit=rate_limit,
            max_retries=max_retries,
            retry_delay=retry_delay,
        )

        self._event_details_parser = EventDetailsParser(
            cache_enabled=cache_enabled,
            cache_dir=cache_dir,
            rate_limit=rate_limit,
            max_retries=max_retries,
            retry_delay=retry_delay,
        )

        self._race_results_parser = RaceResultsParser(
            cache_enabled=cache_enabled,
            cache_dir=cache_dir,
            rate_limit=rate_limit,
            max_retries=max_retries,
            retry_delay=retry_delay,
        )

    def get_events(self, state: str, year: int) -> list[Event]:
        """Get a list of cycling events for a specific state and year.

        Args:
            state: Two-letter state code (e.g., 'CA', 'NY')
            year: Year to search for events (e.g., 2020)

        Returns:
            List of Event objects

        Raises:
            NetworkError: If there's an issue with the network request
            ParseError: If there's an issue parsing the response

        """
        # Validate inputs
        if not state or len(state) != 2:
            raise ValidationError("State must be a two-letter code")

        try:
            # Parse event listings
            events_data = self._event_list_parser.get_events(state, year)

            # Convert to Event model objects
            events = []
            for event_data in events_data:
                try:
                    # Ensure event data has required fields
                    if not event_data.get("id") or not event_data.get("name"):
                        logger.warning(f"Skipping event with incomplete data: {event_data}")
                        continue

                    # Convert event_date to date object if it's provided as a string
                    if "event_date" in event_data and isinstance(event_data["event_date"], str):
                        event_data["date"] = self._parse_date(event_data["event_date"])
                    elif "event_date" in event_data:
                        event_data["date"] = event_data["event_date"]

                    # Create Event object
                    event = Event(
                        id=event_data["id"],
                        name=event_data["name"],
                        permit_id=event_data.get("permit", ""),
                        date=event_data.get("date", None),
                        submit_date=event_data.get("submit_date", None),
                        location=event_data.get("location", "Unknown"),
                        state=state,
                        year=year,
                        url=event_data.get("permit_url", None),
                        html=event_data.get("html", None),
                    )
                    events.append(event)
                except Exception as e:
                    logger.warning(f"Error creating Event object: {e!s}")
                    continue

            return events

        except (NetworkError, ParseError) as e:
            logger.error(f"Error getting events for {state} in {year}: {e!s}")
            raise

    def get_event_details(self, permit_id: str) -> EventDetails:
        """Get detailed information about a specific event.

        Args:
            permit_id: Permit number (e.g., '2020-26')

        Returns:
            EventDetails object

        Raises:
            NetworkError: If there's an issue with the network request
            ParseError: If there's an issue parsing the response

        """
        try:
            # Parse event details
            event_data = self._event_details_parser.get_event_details(permit_id)

            # Convert to EventDetails model object
            event_details = EventDetails(**event_data)

            return event_details

        except (NetworkError, ParseError) as e:
            logger.error(f"Error getting event details for permit {permit_id}: {e!s}")
            raise

    def get_race_categories(self, info_id: str, label: str) -> list[RaceCategory]:
        """Get race categories for a discipline within an event.

        Args:
            info_id: The info ID for the discipline
            label: The label for the discipline

        Returns:
            List of RaceCategory objects

        Raises:
            NetworkError: If there's an issue with the network request
            ParseError: If there's an issue parsing the response

        """
        try:
            # Parse race categories
            categories_data = self._race_results_parser.parse_race_categories(info_id, label)
            # Convert to RaceCategory model objects
            categories = []
            for category_data in categories_data:
                try:
                    # Extract event_id from category_data if available
                    event_id = category_data.get("event_id", "")
                    if not event_id and "info_id" in category_data:
                        # If no event_id is available, use the info_id as a fallback
                        event_id = category_data["info_id"]

                    # Create RaceCategory object
                    category = RaceCategory(
                        id=category_data["id"],
                        name=category_data["name"],
                        event_id=event_id,
                        discipline=category_data.get("discipline", None),
                        gender=category_data.get("gender", None),
                        category_type=category_data.get("category_type", None),
                        age_range=category_data.get("age_range", None),
                        category_rank=category_data.get("category_rank", None),
                    )
                    categories.append(category)
                except Exception as e:
                    logger.warning(f"Error creating RaceCategory object: {e!s}")
                    continue

            return categories

        except (NetworkError, ParseError) as e:
            logger.error(f"Error getting race categories for info_id {info_id}: {e!s}")
            raise

    def get_race_results(self, race_id: str, category_info: dict[str, Any] | None = None) -> RaceResult:
        """Get race results for a specific race.

        Args:
            race_id: ID of the race
            category_info: Optional category information to include

        Returns:
            RaceResult object

        Raises:
            NetworkError: If there's an issue with the network request
            ParseError: If there's an issue parsing the response

        """
        try:
            # Parse race results
            race_data = self._race_results_parser.get_race_results(race_id, category_info)

            # Ensure we have the required fields
            # if not race_data.get('category') or not race_data.get('id'):
            #     raise ParseError(f"Incomplete race data for race ID {race_id}")

            # Set default values for required fields if they're missing
            if "event_id" not in race_data or not race_data["event_id"]:
                race_data["event_id"] = race_data["id"]  # Use race_id as fallback

            if "date" not in race_data or not race_data["date"]:
                # Use current date as fallback
                race_data["date"] = date.today()

            # Convert riders to Rider model objects
            riders = []
            for rider_data in race_data.get("riders", []):
                try:
                    rider = Rider(**rider_data)
                    riders.append(rider)
                except pydantic_ValidationError as exc:
                    logger.warning(f"ValidationError: {exc.errors()[0]['type']!r}")
                except Exception as e:
                    logger.warning(f"Error creating Rider object: {e!s}")
                    continue

            # Create RaceResult object
            race_result = RaceResult(
                id=race_data["id"],
                event_id=race_data["event_id"],
                category=race_data["category"],
                date=race_data["date"],
                riders=riders,
            )

            return race_result

        except (NetworkError, ParseError) as e:
            logger.error(f"Error getting race results for race ID {race_id}: {e!s}")
            raise

    def get_rider_results(self, rider_name: str, year: int | None = None) -> list[tuple[Event, RaceResult]]:
        """Search for race results for a specific rider name.

        This is a placeholder for future functionality. The USA Cycling legacy site
        does not provide direct rider search, so this would require downloading and
        parsing all results for a given year/state.

        Args:
            rider_name: Name of the rider to search for
            year: Optional year to limit the search

        Returns:
            List of tuples containing Event and RaceResult objects

        Raises:
            NotImplementedError: This method is not yet implemented

        """
        raise NotImplementedError("Rider search is not yet implemented")

    def get_disciplines_for_event(self, permit: str) -> list[dict[str, Any]]:
        """Get disciplines for an event.

        Args:
            permit: USA Cycling permit number (e.g., '2020-26')

        Returns:
            List of discipline dictionaries containing:
                - id: Info ID for the discipline
                - name: Discipline name
                - label: Discipline label (includes date)

        """
        try:
            # Fetch the permit page
            html = self._event_details_parser.fetch_permit_page(permit)

            # Parse the disciplines from the page
            soup = BeautifulSoup(html, "html.parser")

            # Extract the onclick attribute from discipline links
            disciplines = []
            discipline_links = soup.select('a[onclick^="loadInfoID"]')

            for link in discipline_links:
                # Extract info_id and label from the onclick attribute
                onclick = link.get("onclick", "")
                info_id_match = re.search(r"loadInfoID\((\d+)", onclick)
                label_match = re.search(r'loadInfoID\(\d+,\s*[\'"]([^\'"]+)[\'"]', onclick)

                if info_id_match:
                    info_id = info_id_match.group(1)
                    label = label_match.group(1) if label_match else ""
                    name = link.get_text(strip=True)

                    # Remove date from name if present
                    name = re.sub(r"\s+\d{2}/\d{2}/\d{4}$", "", name)

                    disciplines.append(
                        {
                            "id": info_id,
                            "name": name,
                            "label": label,
                        }
                    )

            return disciplines

        except (NetworkError, ParseError) as e:
            logger.error(f"Error getting disciplines for permit {permit}: {e!s}")
            raise

    def get_races_for_permit(self, permit: str) -> list[dict[str, Any]]:
        """Get available races for a permit.

        This method scans the permit page and associated discipline pages
        to find all available race IDs.

        Args:
            permit: USA Cycling permit number (e.g., '2020-26')

        Returns:
            List of race dictionaries containing:
                - id: Race ID
                - discipline_id: Discipline info ID
                - name: Race name (if available)
                - permit: Permit number

        """
        try:
            # First get all disciplines
            disciplines = self.get_disciplines_for_event(permit)

            # For each discipline, try to extract race IDs
            races = []

            for discipline in disciplines:
                info_id = discipline.get("id")
                label = discipline.get("label")

                if not info_id or not label:
                    continue

                try:
                    # Try to get categories which may contain race IDs
                    categories = self.get_race_categories(info_id, label)

                    # Extract races from categories
                    for category in categories:
                        # Access attributes directly instead of using .get()
                        race_id = category.id if hasattr(category, "id") else None
                        if race_id:
                            races.append(
                                {
                                    "id": race_id,
                                    "discipline_id": info_id,
                                    "discipline_name": discipline.get("name"),
                                    "name": category.name if hasattr(category, "name") else "",
                                    "permit": permit,
                                }
                            )
                except Exception as e:
                    logger.warning(f"Error getting categories for discipline {info_id}: {e!s}")

                    # If categories didn't work, try another approach
                    try:
                        # Directly check for race links in the permit page
                        html = self._event_details_parser.fetch_permit_page(permit)
                        soup = BeautifulSoup(html, "html.parser")

                        # Look for onclick functions that might contain race IDs
                        race_links = soup.select(f'a[onclick*="{info_id}"]')
                        for link in race_links:
                            onclick = link.get("onclick", "")
                            race_id_match = re.search(r"race_(\d+)", onclick)

                            if race_id_match:
                                race_id = race_id_match.group(1)
                                races.append(
                                    {
                                        "id": race_id,
                                        "discipline_id": info_id,
                                        "discipline_name": discipline.get("name"),
                                        "name": link.get_text(strip=True),
                                        "permit": permit,
                                    }
                                )
                    except Exception as nested_e:
                        logger.warning(f"Error finding race links for discipline {info_id}: {nested_e!s}")

            # Check if we have any races
            if not races:
                # Try a different approach - load the infoid URL directly
                for discipline in disciplines:
                    info_id = discipline.get("id")
                    label = discipline.get("label")

                    if not info_id or not label:
                        continue

                    try:
                        # This will directly fetch the page that contains race IDs
                        info_html = self._race_results_parser.fetch_load_info(info_id, label)
                        if isinstance(info_html, dict) and "categories" in info_html:
                            for cat in info_html["categories"]:
                                race_id = cat.get("id")
                                if race_id:
                                    races.append(
                                        {
                                            "id": race_id,
                                            "discipline_id": info_id,
                                            "discipline_name": discipline.get("name"),
                                            "name": cat.get("name", ""),
                                            "permit": permit,
                                        }
                                    )
                    except Exception as e:
                        logger.warning(f"Error directly fetching info for discipline {info_id}: {e!s}")

            return races

        except (NetworkError, ParseError) as e:
            logger.error(f"Error getting races for permit {permit}: {e!s}")
            raise

    def get_complete_event_data(self, permit: str, include_results: bool = True) -> dict[str, Any]:
        """Get complete event data, including details, disciplines, categories, and optionally results.

        Args:
            permit: USA Cycling permit number (e.g., '2020-26')
            include_results: Whether to include race results

        Returns:
            Dictionary containing event data (details, disciplines, categories, results)

        Raises:
            NetworkError: If there's an issue with the network request
            ParseError: If there's an issue parsing the response

        """
        try:
            # Get event details
            details = self.get_event_details(permit)

            # Get disciplines for the event
            disciplines = self.get_disciplines_for_event(permit)
            # Get categories for each discipline
            categories = []
            for discipline in disciplines:
                info_id = discipline.get("id")
                label = discipline.get("label")

                if not info_id or not label:
                    continue

                try:
                    discipline_categories = self.get_race_categories(info_id, label)
                    categories.extend(discipline_categories)
                except Exception as e:
                    logger.warning(f"Error getting categories for discipline {info_id}: {e!s}")

            # Initialize results dictionary
            results = {}

            # Fetch results if requested
            if include_results:
                # Debug print to see what categories contain
                # If we found categories, use them to get results
                if categories:
                    for category in categories:
                        # Access attributes directly instead of using .get()
                        race_id = category.id if hasattr(category, "id") else None
                        if not race_id:
                            continue

                        try:
                            race_results = self.get_race_results(race_id, category_info=category)
                            results[race_id] = race_results
                        except Exception as e:
                            logger.warning(f"Error getting results for race {race_id}: {e!s}")
                else:
                    # If no categories were found through normal means, try using races instead
                    logger.info("No categories found, attempting to get race IDs directly")

                    races = self.get_races_for_permit(permit)
                    if races:
                        for race in races:
                            race_id = race.get("id")
                            if not race_id:
                                continue

                            try:
                                race_results = self.get_race_results(race_id)
                                results[race_id] = race_results
                            except Exception as e:
                                logger.warning(f"Error getting results for race {race_id}: {e!s}")

            # Combine all data
            return {"event": details, "disciplines": disciplines, "categories": categories, "results": results}

        except (NetworkError, ParseError) as e:
            logger.error(f"Error getting complete event data for permit {permit}: {e!s}")
            raise

    def _parse_date(self, date_str: str) -> date:
        """Parse a date string using the BaseParser's _extract_date method.

        Args:
            date_str: Date string to parse

        Returns:
            date object or today's date if parsing fails

        """
        # Create a temporary BaseParser instance
        parser = BaseParser(cache_enabled=False)

        # Parse the date
        parsed_date = parser._extract_date(date_str)

        # Return the parsed date or today's date if parsing fails
        return parsed_date or date.today()

    def get_active_events(self) -> list[EventDetails]:
        """Get active events from the USA Cycling website."""
        pass  # TODO: Implement this method

    def fetch_flyer(
        self,
        permit: str,
        storage_dir: str = "./flyers",
        use_s3: bool = False,
        s3_bucket: str | None = None,
        s3_prefix: str = "flyers",
    ) -> dict[str, Any]:
        """Fetch a flyer for a specific event permit.

        This method fetches a flyer (promotional material) for a USA Cycling event permit.
        The flyer can be in various formats (PDF, DOC, DOCX, HTML) and is stored locally
        or in S3 with gzip compression.

        Args:
            permit: USA Cycling permit number (e.g., 2020-123)
            storage_dir: Directory to store flyers locally
            use_s3: Whether to store flyers in S3
            s3_bucket: S3 bucket name (required if use_s3 is True)
            s3_prefix: S3 prefix for flyer storage

        Returns:
            Dictionary with fetched flyer details

        Raises:
            NetworkError: If there's a network error
            ParseError: If there's an error parsing the response

        """
        fetcher = FlyerFetcher(
            cache_enabled=self.cache_enabled,
            cache_dir=self.cache_dir,
            rate_limit=self.rate_limit,
            max_retries=self.max_retries,
            retry_delay=self.retry_delay,
            storage_dir=storage_dir,
            use_s3=use_s3,
            s3_bucket=s3_bucket,
            s3_prefix=s3_prefix,
        )

        return fetcher.fetch_flyer(permit)

    def fetch_flyers_batch(
        self,
        start_year: int,
        end_year: int,
        limit: int = 100,
        delay: int = 3,
        storage_dir: str = "./flyers",
        use_s3: bool = False,
        s3_bucket: str | None = None,
        s3_prefix: str = "flyers",
    ) -> dict[str, Any]:
        """Fetch flyers for events in a year range.

        This method fetches flyers for USA Cycling events in the specified year range.
        It retrieves event information from the USA Cycling website and fetches flyers
        for each event up to the specified limit.

        Args:
            start_year: Start year for fetching flyers
            end_year: End year for fetching flyers
            limit: Maximum number of flyers to fetch
            delay: Delay between requests in seconds
            storage_dir: Directory to store flyers locally
            use_s3: Whether to store flyers in S3
            s3_bucket: S3 bucket name (required if use_s3 is True)
            s3_prefix: S3 prefix for flyer storage

        Returns:
            Dictionary with statistics about the fetched flyers

        Raises:
            NetworkError: If there's a network error
            ParseError: If there's an error parsing the response

        """
        fetcher = FlyerFetcher(
            cache_enabled=self.cache_enabled,
            cache_dir=self.cache_dir,
            rate_limit=self.rate_limit,
            max_retries=self.max_retries,
            retry_delay=self.retry_delay,
            storage_dir=storage_dir,
            use_s3=use_s3,
            s3_bucket=s3_bucket,
            s3_prefix=s3_prefix,
        )

        return fetcher.fetch_flyers_batch(
            start_year=start_year,
            end_year=end_year,
            limit=limit,
            delay=delay,
        )

    def list_flyers(
        self,
        storage_dir: str = "./flyers",
        use_s3: bool = False,
        s3_bucket: str | None = None,
        s3_prefix: str = "flyers",
    ) -> list[dict[str, Any]]:
        """List all flyers in storage.

        This method lists all flyers stored locally or in S3.

        Args:
            storage_dir: Directory where flyers are stored locally
            use_s3: Whether flyers are stored in S3
            s3_bucket: S3 bucket name (required if use_s3 is True)
            s3_prefix: S3 prefix for flyer storage

        Returns:
            List of flyer details

        """
        fetcher = FlyerFetcher(
            cache_enabled=self.cache_enabled,
            cache_dir=self.cache_dir,
            rate_limit=self.rate_limit,
            max_retries=self.max_retries,
            retry_delay=self.retry_delay,
            storage_dir=storage_dir,
            use_s3=use_s3,
            s3_bucket=s3_bucket,
            s3_prefix=s3_prefix,
        )

        return fetcher.list_flyers()
