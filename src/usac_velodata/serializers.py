"""Serializers for the USA Cycling Results Parser package.

This module provides serialization capabilities for the data models.
"""

import csv
import io
import json
from datetime import date, datetime
from enum import Enum
from typing import Any, TypeVar, cast

from pydantic import BaseModel

from src.usac_velodata.models import Event, EventDetails, RaceCategory, RaceResult, Rider, SeriesResults

# Type variable for our models
M = TypeVar("M", bound=BaseModel)


class EnhancedJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles Python types like dates, datetimes, and Enum values.

    This encoder is used internally by the serialization functions to properly convert
    Python objects to JSON-compatible data types.
    """

    def default(self, obj: Any) -> Any:
        """Convert Python objects to JSON-compatible types."""
        if isinstance(obj, BaseModel):
            # Convert Pydantic models using their built-in model_dump method
            return obj.model_dump()
        elif isinstance(obj, datetime):
            # Convert datetime to ISO format
            return obj.isoformat()
        elif isinstance(obj, date):
            # Convert date to ISO format
            return obj.isoformat()
        elif isinstance(obj, Enum):
            # Convert Enum to its value
            return obj.value
        # Let the base class handle other types or raise TypeError
        return super().default(obj)


def to_json(
    obj: BaseModel | list[BaseModel] | dict[str, Any],
    pretty: bool = False,
    sort_keys: bool = False,
    encode_json: bool = True,
    **kwargs: Any,
) -> str | dict[str, Any]:
    """Convert a model, list of models, or dict to JSON string or dict.

    Args:
        obj: The Pydantic model, list of models, or dict to serialize
        pretty: If True, format the JSON with indentation for readability
        sort_keys: If True, sort the keys alphabetically in the JSON output
        encode_json: If True, return a JSON string; if False, return a dict
        **kwargs: Additional arguments to pass to json.dumps()

    Returns:
        JSON string or dict representation of the model(s)

    Examples:
        >>> event = Event(id="123", name="Race", ...)
        >>> json_str = to_json(event)
        >>>
        >>> # Get a dictionary instead of a JSON string
        >>> event_dict = to_json(event, encode_json=False)
        >>>
        >>> # Pretty-print the JSON
        >>> pretty_json = to_json(event, pretty=True)

    """
    indent = 2 if pretty else None

    # Convert model or models to dict first if needed
    if isinstance(obj, BaseModel):
        data = obj.model_dump()
    elif isinstance(obj, list) and all(isinstance(item, BaseModel) for item in obj):
        data = [item.model_dump() for item in obj]
    else:
        # Assume it's already a dict or JSON-compatible structure
        data = obj

    # Convert to JSON string if requested
    if encode_json:
        return json.dumps(data, cls=EnhancedJSONEncoder, indent=indent, sort_keys=sort_keys, **kwargs)

    # Otherwise return the dict representation
    return data


def from_json(
    json_data: str | dict[str, Any] | list[dict[str, Any]], model_class: type[M], many: bool = False
) -> M | list[M]:
    """Convert JSON data to a Pydantic model or list of models.

    Args:
        json_data: JSON string or dict to deserialize
        model_class: The Pydantic model class to instantiate
        many: If True, treat the input as a list of models

    Returns:
        Instantiated model or list of models

    Examples:
        >>> json_str = '{"id": "123", "name": "Race", ...}'
        >>> event = from_json(json_str, Event)
        >>>
        >>> # Deserialize a list of events
        >>> events_json = '[{"id": "1"...}, {"id": "2"...}]'
        >>> events = from_json(events_json, Event, many=True)

    """
    # Parse JSON string if needed
    data = json.loads(json_data) if isinstance(json_data, str) else json_data

    # Handle list of models
    if many:
        if not isinstance(data, list):
            raise ValueError("Expected a list of data when many=True")
        return [model_class.model_validate(item) for item in data]

    # Handle single model
    return model_class.model_validate(data)


def model_to_dict(
    obj: BaseModel | list[BaseModel], exclude_none: bool = False
) -> dict[str, Any] | list[dict[str, Any]]:
    """Convert a model or list of models to a dictionary.

    Args:
        obj: The Pydantic model or list of models to convert
        exclude_none: If True, exclude fields with None values

    Returns:
        Dictionary or list of dictionaries

    Examples:
        >>> event = Event(id="123", name="Race", ...)
        >>> event_dict = model_to_dict(event)
        >>>
        >>> # Exclude None values
        >>> event_dict_no_nones = model_to_dict(event, exclude_none=True)

    """
    if isinstance(obj, list):
        return [item.model_dump(exclude_none=exclude_none) if isinstance(item, BaseModel) else item for item in obj]
    elif isinstance(obj, BaseModel):
        return obj.model_dump(exclude_none=exclude_none)
    else:
        # Just return the object if it's not a model
        return cast(dict[str, Any], obj)


# CSV Serialization Functions


def _flatten_dict(data: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    """Flatten a nested dictionary structure into a flat structure with keys using dot notation.

    Args:
        data: The dictionary to flatten
        prefix: Prefix to prepend to all keys (used for recursion)

    Returns:
        A flattened dictionary

    """
    result = {}
    for key, value in data.items():
        new_key = f"{prefix}.{key}" if prefix else key

        if isinstance(value, dict):
            # Recursively flatten nested dictionaries
            result.update(_flatten_dict(value, new_key))
        elif isinstance(value, list):
            # For lists, create entries list.0, list.1, etc.
            # Only go one level deep for simplicity
            for i, item in enumerate(value[:5]):  # Limit to first 5 items
                if isinstance(item, dict):
                    for k, v in item.items():
                        if not isinstance(v, dict | list):  # Avoid nested structures
                            result[f"{new_key}.{i}.{k}"] = v
                else:
                    result[f"{new_key}.{i}"] = item
            # Add count
            result[f"{new_key}_count"] = len(value)
        else:
            # Simple values
            result[new_key] = value

    return result


def to_csv(
    obj: BaseModel | list[BaseModel] | dict | list[dict],
    include_header: bool = True,
    exclude_none: bool = False,
) -> str:
    """Convert a model or list of models to CSV format.

    Args:
        obj: The Pydantic model, dictionary, or list of models/dictionaries to convert to CSV
        include_header: Whether to include header row with field names
        exclude_none: Whether to exclude None values

    Returns:
        CSV string representation of the model(s)

    """
    # Convert to list if single model/dict
    items = [obj] if not isinstance(obj, list) else obj

    # Handle empty list
    if not items:
        return ""

    # Convert models to dictionaries if needed
    dicts = []
    for item in items:
        if isinstance(item, BaseModel):
            dicts.append(item.model_dump(exclude_none=exclude_none))
        else:
            dicts.append(item)

    # Get field names from first dictionary
    field_names = list(dicts[0].keys())

    # Create CSV writer
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=field_names)

    # Write header if requested
    if include_header:
        writer.writeheader()

    # Write data rows
    writer.writerows(dicts)

    return output.getvalue()


def from_csv(
    csv_data: str,
    model_class: type[M],
    has_header: bool = True,
) -> list[M]:
    r"""Convert CSV data to a list of Pydantic models.

    Args:
        csv_data: CSV string to parse
        model_class: The Pydantic model class to instantiate
        has_header: Whether the CSV has a header row

    Returns:
        List of instantiated models

    Examples:
        >>> csv_str = "id,name,date\n123,Race,2023-01-15"
        >>> events = from_csv(csv_str, Event)

    """
    if not csv_data.strip():
        return []

    # Parse CSV
    reader = csv.reader(io.StringIO(csv_data))
    rows = list(reader)

    if not rows:
        return []

    # Extract header and data rows
    if has_header:
        header = rows[0]
        data_rows = rows[1:]
    else:
        # If no header, use model fields as header
        model_fields = model_class.__annotations__.keys()
        header = list(model_fields)
        data_rows = rows

    # Convert to list of dictionaries
    dict_rows = []
    for row in data_rows:
        # Zip header with values, but only take relevant fields for the model
        row_data = {name: value for name, value in zip(header, row, strict=False) if "." not in name}
        dict_rows.append(row_data)

    # Convert to models
    models = []
    for row_dict in dict_rows:
        try:
            # Try to create a model from the row data
            model = model_class.model_validate(row_dict)
            models.append(model)
        except Exception:
            # Skip invalid rows
            continue

    return models


# Specific serialization functions for each model type


def serialize_event(
    event: Event | list[Event], pretty: bool = False, encode_json: bool = True
) -> str | dict[str, Any] | list[dict[str, Any]]:
    """Serialize an Event or list of Events to JSON.

    Args:
        event: Event model(s) to serialize
        pretty: If True, format the JSON with indentation
        encode_json: If True, return a JSON string; if False, return a dict

    Returns:
        JSON string or dict representation of the Event(s)

    """
    return to_json(event, pretty=pretty, encode_json=encode_json)


def serialize_event_details(
    event_details: EventDetails | list[EventDetails], pretty: bool = False, encode_json: bool = True
) -> str | dict[str, Any] | list[dict[str, Any]]:
    """Serialize an EventDetails or list of EventDetails to JSON.

    Args:
        event_details: EventDetails model(s) to serialize
        pretty: If True, format the JSON with indentation
        encode_json: If True, return a JSON string; if False, return a dict

    Returns:
        JSON string or dict representation of the EventDetails

    """
    return to_json(event_details, pretty=pretty, encode_json=encode_json)


def serialize_race_result(
    race_result: RaceResult | list[RaceResult], pretty: bool = False, encode_json: bool = True
) -> str | dict[str, Any] | list[dict[str, Any]]:
    """Serialize a RaceResult or list of RaceResults to JSON.

    Args:
        race_result: RaceResult model(s) to serialize
        pretty: If True, format the JSON with indentation
        encode_json: If True, return a JSON string; if False, return a dict

    Returns:
        JSON string or dict representation of the RaceResult(s)

    """
    return to_json(race_result, pretty=pretty, encode_json=encode_json)


def serialize_rider(
    rider: Rider | list[Rider], pretty: bool = False, encode_json: bool = True
) -> str | dict[str, Any] | list[dict[str, Any]]:
    """Serialize a Rider or list of Riders to JSON.

    Args:
        rider: Rider model(s) to serialize
        pretty: If True, format the JSON with indentation
        encode_json: If True, return a JSON string; if False, return a dict

    Returns:
        JSON string or dict representation of the Rider(s)

    """
    return to_json(rider, pretty=pretty, encode_json=encode_json)


def serialize_race_category(
    category: RaceCategory | list[RaceCategory], pretty: bool = False, encode_json: bool = True
) -> str | dict[str, Any] | list[dict[str, Any]]:
    """Serialize a RaceCategory or list of RaceCategories to JSON.

    Args:
        category: RaceCategory model(s) to serialize
        pretty: If True, format the JSON with indentation
        encode_json: If True, return a JSON string; if False, return a dict

    Returns:
        JSON string or dict representation of the RaceCategory(s)

    """
    return to_json(category, pretty=pretty, encode_json=encode_json)


def serialize_series_results(
    series: SeriesResults | list[SeriesResults], pretty: bool = False, encode_json: bool = True
) -> str | dict[str, Any] | list[dict[str, Any]]:
    """Serialize SeriesResults or list of SeriesResults to JSON.

    Args:
        series: SeriesResults model(s) to serialize
        pretty: If True, format the JSON with indentation
        encode_json: If True, return a JSON string; if False, return a dict

    Returns:
        JSON string or dict representation of the SeriesResults

    """
    return to_json(series, pretty=pretty, encode_json=encode_json)


# Specific CSV serialization functions for each model type


def serialize_event_to_csv(
    event: Event | list[Event],
    include_header: bool = True,
) -> str:
    """Serialize an Event or list of Events to CSV.

    Args:
        event: Event model(s) to serialize
        include_header: Whether to include header row

    Returns:
        CSV string representation of the Event(s)

    """
    return to_csv(event, include_header=include_header)


def serialize_event_details_to_csv(event_details: EventDetails) -> str:
    """Serialize EventDetails to CSV format.

    Args:
        event_details: The EventDetails to serialize.

    Returns:
        A CSV string containing the serialized data.

    """
    # Convert to dict and flatten nested structures
    data = event_details.model_dump()

    # Flatten arrays
    if "categories" in data:
        categories = data.pop("categories")
        for i, category in enumerate(categories):
            data[f"categories.{i}"] = category

    if "disciplines" in data:
        disciplines = data.pop("disciplines")
        for i, discipline in enumerate(disciplines):
            for key, value in discipline.items():
                data[f"disciplines.{i}.{key}"] = value

    if "dates" in data:
        dates = data.pop("dates")
        for i, date in enumerate(dates):
            data[f"dates.{i}"] = date

    return to_csv([data])


def serialize_race_result_to_csv(race_result: RaceResult) -> str:
    """Serialize a RaceResult to CSV format.

    Args:
        race_result: The RaceResult to serialize.

    Returns:
        A CSV string containing the serialized data.

    """
    # Convert to dict and flatten nested structures
    data = race_result.model_dump()

    # Flatten category
    if "category" in data:
        category_data = data.pop("category")
        for key, value in category_data.items():
            data[f"category.{key}"] = value

    # Flatten riders
    if "riders" in data:
        riders = data.pop("riders")
        for i, rider in enumerate(riders):
            for key, value in rider.items():
                data[f"riders.{i}.{key}"] = value

    # Convert to list of dicts for to_csv
    return to_csv([data])


def serialize_rider_to_csv(
    rider: Rider | list[Rider],
    include_header: bool = True,
) -> str:
    """Serialize a Rider or list of Riders to CSV.

    Args:
        rider: Rider model(s) to serialize
        include_header: Whether to include header row

    Returns:
        CSV string representation of the Rider(s)

    """
    return to_csv(rider, include_header=include_header)


def serialize_race_category_to_csv(
    category: RaceCategory | list[RaceCategory],
    include_header: bool = True,
) -> str:
    """Serialize a RaceCategory or list of RaceCategories to CSV.

    Args:
        category: RaceCategory model(s) to serialize
        include_header: Whether to include header row

    Returns:
        CSV string representation of the RaceCategory(s)

    """
    return to_csv(category, include_header=include_header)


def serialize_series_results_to_csv(
    series: SeriesResults | list[SeriesResults],
    include_header: bool = True,
) -> str:
    """Serialize SeriesResults or list of SeriesResults to CSV.

    Args:
        series: SeriesResults model(s) to serialize
        include_header: Whether to include header row

    Returns:
        CSV string representation of the SeriesResults

    """
    return to_csv(series, include_header=include_header)
