"""Pydantic models for the USA Cycling Results Parser package."""

from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, HttpUrl, field_validator


class Address(BaseModel):
    """Model for a physical address."""

    street: str | None = None
    street2: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    latitude: float | None = None
    longitude: float | None = None

    class Config:
        """Pydantic model configuration."""

        frozen = True


class EventDate(BaseModel):
    """Model for an event date with location."""

    date_id: str | None = None
    description: str | None = None
    start_date: date
    end_date: date
    address: Address | None = None

    class Config:
        """Pydantic model configuration."""

        frozen = True


class EventType(str, Enum):
    """Enum for event types."""

    ROAD = "road"
    MOUNTAIN = "mountain"
    CYCLOCROSS = "cyclocross"
    TRACK = "track"
    BMX = "bmx"
    GRAVEL = "gravel"
    OTHER = "other"


class EventLinks(BaseModel):
    """Model for event-related links."""

    logo_url: HttpUrl | None = None
    badge_url: HttpUrl | None = None
    register_url: HttpUrl | None = None
    website_url: HttpUrl | None = None
    social_urls: list[dict[str, str]] = Field(default_factory=list)

    class Config:
        """Pydantic model configuration."""

        frozen = True


class ApiEvent(BaseModel):
    """Model for an event from the USA Cycling API."""

    event_id: str
    name: str
    start_date: date
    end_date: date
    dates: list[EventDate] = Field(default_factory=list)
    is_featured: bool = False
    is_weekend: bool = False
    is_multiday: bool = False
    is_usac_sanctioned: bool = False
    event_organizer_email: str | None = None
    event_status: str
    permit: str
    labels: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    links: EventLinks | None = None
    data_source: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        """Pydantic model configuration."""

        frozen = True

    @classmethod
    @field_validator("start_date", "end_date", mode="before")
    def parse_date(cls, value: Any) -> date:
        """Parse date from string if needed."""
        if isinstance(value, str):
            return datetime.strptime(value, "%Y-%m-%d").date()
        return value  # type: ignore


class EventSearchResponse(BaseModel):
    """Model for the event search API response."""

    data: list[ApiEvent] = Field(default_factory=list)
    filters: dict[str, Any] = Field(default_factory=dict)

    class Config:
        """Pydantic model configuration."""

        frozen = True


class Event(BaseModel):
    """Model for a USA Cycling event (simplified version).

    This is obtained from a year, state event list page.
    """

    id: str
    permit_id: str
    year: int
    state: str
    name: str
    date: date | None
    submit_date: date | None
    location: str  # TODO: I dont think this ever has a value
    event_type: EventType | None = None  # TODO: I dont think this ever has a value
    url: str | None = None
    html: str | None = None  # This is the table row.

    class Config:
        """Pydantic model configuration."""

        frozen = True


class EventDetails(BaseModel):
    """Model for detailed event information."""

    id: str
    name: str
    permit_id: str
    start_date: date | None = None
    end_date: date | None = None
    location: str | None = None
    state: str | None = None
    year: int | None = None
    event_type: EventType | None = None
    promoter: str | None = None
    promoter_email: str | None = None
    website: str | None = None
    registration_url: str | None = None
    is_usac_sanctioned: bool = False
    categories: Any = Field(default_factory=list)
    disciplines: list[dict[str, str]] = Field(default_factory=list)
    description: str | None = None
    dates: list[EventDate] = Field(default_factory=list)

    class Config:
        """Pydantic model configuration."""

        frozen = True


class RaceCategory(BaseModel):
    """Model for a race category."""

    id: str
    name: str
    event_id: str
    race_date: date | None = None
    distance: str | None = None
    participants_count: int | None = None
    category_type: str | None = None
    discipline: str | None = None
    gender: str | None = None
    age_range: str | None = None
    category_rank: str | None = None

    class Config:
        """Pydantic model configuration."""

        frozen = True


class RaceTime(BaseModel):
    """Model for race timing information."""

    raw_time: str | None = None
    formatted_time: str | None = None
    seconds: float | None = None
    gap_to_leader: str | None = None

    class Config:
        """Pydantic model configuration."""

        frozen = True


class RiderResult(BaseModel):
    """Model for a single rider's result in a race."""

    place: str
    place_number: int | None = None
    is_dnf: bool = False
    is_dns: bool = False
    is_dq: bool = False
    points: int | None = None
    premium_points: int | None = None
    time: RaceTime | None = None

    class Config:
        """Pydantic model configuration."""

        frozen = True


class Rider(BaseModel):
    """Model for a race participant."""

    place: str
    name: str
    first_name: str | None = None
    last_name: str | None = None
    city: str | None = None
    state: str | None = None
    team: str | None = None
    team_id: str | None = None
    license: str | None = None
    license_type: str | None = None
    racing_age: int | None = None
    bib: str | None = None
    time: str | None = None
    result: RiderResult | None = None

    class Config:
        """Pydantic model configuration."""

        frozen = True

    @classmethod
    @field_validator("place", mode="before")
    def parse_place(cls, value: Any) -> str:
        """Convert place to string and handle special cases."""
        if value is None:
            return "N/A"
        return str(value)


class RaceLap(BaseModel):
    """Model for a lap in a race."""

    lap_number: int
    rider_id: str
    time: str | None = None
    elapsed_time: str | None = None
    seconds: float | None = None

    class Config:
        """Pydantic model configuration."""

        frozen = True


class RaceResult(BaseModel):
    """Model for race results."""

    id: str
    event_id: str
    # category: Optional[RaceCategory] = None
    date: date
    start_time: datetime | None = None
    total_laps: int | None = None
    total_distance: str | None = None
    weather_conditions: str | None = None
    course_description: str | None = None
    riders: list[Rider] = Field(default_factory=list)
    laps: list[RaceLap] = Field(default_factory=list)
    has_time_data: bool = False
    has_lap_data: bool = False

    class Config:
        """Pydantic model configuration."""

        frozen = True


class RaceSeriesStanding(BaseModel):
    """Model for a rider's standing in a race series."""

    series_id: str
    series_name: str
    rider_id: str
    rider_name: str
    position: int
    total_points: int
    races_completed: int
    category: str | None = None
    team: str | None = None

    class Config:
        """Pydantic model configuration."""

        frozen = True


class SeriesResults(BaseModel):
    """Model for results of a race series."""

    id: str
    name: str
    year: int
    categories: list[str] = Field(default_factory=list)
    events: list[str] = Field(default_factory=list)
    standings: list[RaceSeriesStanding] = Field(default_factory=list)

    class Config:
        """Pydantic model configuration."""

        frozen = True
