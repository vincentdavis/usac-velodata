"""Tests for JSON serialization functionality."""

import json
import unittest
from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field

from usac_velodata.models import Event, EventDetails, EventType, RaceCategory, RaceResult, Rider
from usac_velodata.serializers import (
    EnhancedJSONEncoder,
    from_json,
    model_to_dict,
    serialize_event,
    serialize_event_details,
    serialize_race_category,
    serialize_race_result,
    serialize_rider,
    to_json,
)


# Test models for basic serialization
class TestEnum(str, Enum):
    """Test enum for serialization."""

    VALUE1 = "value1"
    VALUE2 = "value2"


class SimpleModel(BaseModel):
    """Simple model for testing serialization."""

    id: str
    name: str
    value: int
    created_at: datetime
    is_active: bool = True
    tags: list[str] = Field(default_factory=list)
    enum_field: TestEnum = TestEnum.VALUE1

    class Config:
        """Pydantic model configuration."""

        frozen = True


class TestJsonSerializer(unittest.TestCase):
    """Test suite for JSON serialization."""

    def setUp(self):
        """Set up test data."""
        # Create a test date and time
        self.test_date = date(2023, 1, 15)
        self.test_datetime = datetime(2023, 1, 15, 12, 30, 45)

        # Create simple test model
        self.simple_model = SimpleModel(
            id="123",
            name="Test Model",
            value=42,
            created_at=self.test_datetime,
            tags=["tag1", "tag2"],
            enum_field=TestEnum.VALUE2,
        )

        # Create test Event
        self.test_event = Event(
            id="event123",
            name="Test Event",
            permit_number="2023-123",
            date=self.test_date,
            location="Somewhere, USA",
            state="WA",
            year=2023,
            event_type=EventType.ROAD,
            url="https://example.com/event",
        )

        # Create test EventDetails
        self.test_event_details = EventDetails(
            id="event123",
            name="Test Event",
            permit_number="2023-123",
            start_date=self.test_date,
            end_date=self.test_date,
            location="Somewhere, USA",
            state="WA",
            year=2023,
            event_type=EventType.ROAD,
            promoter="Test Promoter",
            promoter_email="promoter@example.com",
            website="https://example.com/event",
            registration_url="https://example.com/register",
            is_usac_sanctioned=True,
            categories=["Cat 1/2", "Cat 3", "Cat 4/5"],
            disciplines=[
                {"id": "1", "name": "Road Race"},
                {"id": "2", "name": "Time Trial"}
            ],
            description="A test event",
        )

        # Create test RaceCategory
        self.test_category = RaceCategory(
            id="cat123",
            name="Men's Cat 3",
            event_id="event123",
            race_date=self.test_date,
            distance="50 miles",
            participants_count=30,
            category_type="Road",
            discipline="Road Race",
            gender="Male",
            age_range="18-99",
            category_rank="3",
        )

        # Create test Rider
        self.test_rider = Rider(
            place="1",
            name="John Doe",
            first_name="John",
            last_name="Doe",
            city="Somewhere",
            state="WA",
            team="Test Team",
            license="12345",
            racing_age=35,
            bib="101",
            time="1:30:45",
        )

        # Create a minimal test RaceResult
        self.test_race_result = RaceResult(
            id="result123",
            event_id="event123",
            category=self.test_category,
            date=self.test_date,
            riders=[self.test_rider],
            has_time_data=True,
        )

    def test_enhanced_json_encoder(self):
        """Test EnhancedJSONEncoder with various Python types."""
        # Test with date
        date_json = json.dumps(self.test_date, cls=EnhancedJSONEncoder)
        self.assertEqual(date_json, f'"{self.test_date.isoformat()}"')

        # Test with datetime
        datetime_json = json.dumps(self.test_datetime, cls=EnhancedJSONEncoder)
        self.assertEqual(datetime_json, f'"{self.test_datetime.isoformat()}"')

        # Test with Enum
        enum_json = json.dumps(TestEnum.VALUE1, cls=EnhancedJSONEncoder)
        self.assertEqual(enum_json, f'"{TestEnum.VALUE1.value}"')

        # Test with Pydantic model
        model_json = json.dumps(self.simple_model, cls=EnhancedJSONEncoder)
        model_dict = json.loads(model_json)
        self.assertEqual(model_dict["id"], "123")
        self.assertEqual(model_dict["name"], "Test Model")
        self.assertEqual(model_dict["enum_field"], "value2")

    def test_to_json_basic(self):
        """Test basic to_json functionality."""
        # Test with a simple model
        json_str = to_json(self.simple_model)
        self.assertIsInstance(json_str, str)

        # Verify the JSON can be loaded back into a dict
        data = json.loads(json_str)
        self.assertEqual(data["id"], "123")
        self.assertEqual(data["name"], "Test Model")
        self.assertEqual(data["value"], 42)

    def test_to_json_options(self):
        """Test to_json with different options."""
        # Test pretty printing
        pretty_json = to_json(self.simple_model, pretty=True)
        self.assertIn("\n", pretty_json)

        # Test return as dict
        data_dict = to_json(self.simple_model, encode_json=False)
        self.assertIsInstance(data_dict, dict)
        self.assertEqual(data_dict["id"], "123")

        # Test with sorted keys
        sorted_json = to_json(self.simple_model, sort_keys=True)
        # Check keys are in alphabetical order
        first_key_pos = sorted_json.find('"created_at"')
        second_key_pos = sorted_json.find('"enum_field"')
        self.assertLess(first_key_pos, second_key_pos)

    def test_to_json_list(self):
        """Test to_json with a list of models."""
        models = [self.simple_model, self.simple_model]
        json_str = to_json(models)

        # Verify it's a valid JSON array
        data = json.loads(json_str)
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["id"], "123")

    def test_from_json_basic(self):
        """Test basic from_json functionality."""
        # Convert model to JSON
        json_str = to_json(self.simple_model)

        # Convert back to model
        model = from_json(json_str, SimpleModel)

        # Verify model properties
        self.assertEqual(model.id, "123")
        self.assertEqual(model.name, "Test Model")
        self.assertEqual(model.value, 42)
        self.assertEqual(model.enum_field, TestEnum.VALUE2)

    def test_from_json_list(self):
        """Test from_json with a list of models."""
        # Create a list of models
        models = [self.simple_model, self.simple_model]

        # Convert to JSON
        json_str = to_json(models)

        # Convert back to models
        parsed_models = from_json(json_str, SimpleModel, many=True)

        # Verify models
        self.assertIsInstance(parsed_models, list)
        self.assertEqual(len(parsed_models), 2)
        self.assertEqual(parsed_models[0].id, "123")
        self.assertEqual(parsed_models[1].name, "Test Model")

    def test_from_json_dict(self):
        """Test from_json with a dictionary."""
        # Create a dictionary
        data = {
            "id": "dict123",
            "name": "Dict Model",
            "value": 99,
            "created_at": self.test_datetime.isoformat(),
            "tags": ["tag3", "tag4"],
            "enum_field": "value1",
        }

        # Convert to model
        model = from_json(data, SimpleModel)

        # Verify model properties
        self.assertEqual(model.id, "dict123")
        self.assertEqual(model.name, "Dict Model")
        self.assertEqual(model.value, 99)
        self.assertEqual(model.enum_field, TestEnum.VALUE1)

    def test_model_to_dict(self):
        """Test model_to_dict function."""
        # Convert model to dict
        data = model_to_dict(self.simple_model)

        # Verify dict properties
        self.assertIsInstance(data, dict)
        self.assertEqual(data["id"], "123")
        self.assertEqual(data["name"], "Test Model")

        # Test with empty list - In Pydantic v2, None is not valid for a List field
        model_with_empty = SimpleModel(
            id="456",
            name="Test None",
            value=0,
            created_at=self.test_datetime,
            tags=[],  # Empty list instead of None
        )

        # Test with default behavior
        data_with_all = model_to_dict(model_with_empty)

        # Both should have the tags field as it's an empty list, not None
        self.assertIn("tags", data_with_all)
        self.assertEqual(data_with_all["tags"], [])

    def test_serialize_event(self):
        """Test serialize_event function."""
        # Serialize a single event
        json_str = serialize_event(self.test_event)
        data = json.loads(json_str)

        # Verify event properties
        self.assertEqual(data["id"], "event123")
        self.assertEqual(data["name"], "Test Event")
        self.assertEqual(data["event_type"], "road")

        # Test with a list of events
        events = [self.test_event, self.test_event]
        json_str = serialize_event(events)
        data = json.loads(json_str)

        # Verify list properties
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["id"], "event123")

    def test_serialize_event_details(self):
        """Test serialize_event_details function."""
        # Serialize event details
        json_str = serialize_event_details(self.test_event_details)
        data = json.loads(json_str)

        # Verify event details properties
        self.assertEqual(data["id"], "event123")
        self.assertEqual(data["name"], "Test Event")
        self.assertEqual(data["promoter"], "Test Promoter")
        self.assertIn("Cat 1/2", data["categories"])

    def test_serialize_race_category(self):
        """Test serialize_race_category function."""
        # Serialize race category
        json_str = serialize_race_category(self.test_category)
        data = json.loads(json_str)

        # Verify category properties
        self.assertEqual(data["id"], "cat123")
        self.assertEqual(data["name"], "Men's Cat 3")
        self.assertEqual(data["discipline"], "Road Race")

    def test_serialize_rider(self):
        """Test serialize_rider function."""
        # Serialize rider
        json_str = serialize_rider(self.test_rider)
        data = json.loads(json_str)

        # Verify rider properties
        self.assertEqual(data["place"], "1")
        self.assertEqual(data["name"], "John Doe")
        self.assertEqual(data["team"], "Test Team")

    def test_serialize_race_result(self):
        """Test serialize_race_result function."""
        # Serialize race result
        json_str = serialize_race_result(self.test_race_result)
        data = json.loads(json_str)

        # Verify race result properties
        self.assertEqual(data["id"], "result123")
        self.assertEqual(data["event_id"], "event123")
        self.assertEqual(len(data["riders"]), 1)
        self.assertEqual(data["riders"][0]["name"], "John Doe")


if __name__ == "__main__":
    unittest.main()
