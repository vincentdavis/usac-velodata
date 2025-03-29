# USA Cycling Results Parser (usac_velodata)

A Python package that scrapes and parses USA Cycling event results from the legacy USA Cycling results page and API. The package extracts event details, race results, categories, rankings, and historical data, returning structured data in multiple formats.

[![PyPI version](https://img.shields.io/pypi/v/usac_velodata.svg)](https://pypi.org/project/usac_velodata/)
[![Python versions](https://img.shields.io/pypi/pyversions/usac_velodata.svg)](https://pypi.org/project/usac_velodata/)
[![License](https://img.shields.io/pypi/l/usac_velodata.svg)](https://github.com/yourusername/usac_velodata/blob/main/LICENSE)

## 🚀 Features

- **Event Data**: Fetch event lists by state and year from USA Cycling API
- **Result Parsing**: Extract race results from the legacy USA Cycling results page
- **Comprehensive Data**: Get event details, race categories, and rider information
- **Historical Data**: Support for fetching data across multiple years
- **Flyer Fetching**: Download event flyers in various formats (PDF, HTML, DOC)
- **Flexible Output**: Export data in multiple formats (Pydantic models, JSON, CSV)
- **Resilient Fetching**: Built-in retry mechanism and rate limiting
- **Efficient Caching**: Local storage of results to minimize requests
- **Type Safety**: Fully type-annotated API with Pydantic validation

## 📦 Installation

### Standard installation

### using uv
```
uv pip install usac_velodata
```

### Using Pip
```bash
pip install usac_velodata
```

### For development

```bash
git clone https://github.com/vincentdavis/pyusacycling.git
cd usac_velodata
uv build
```

## 🔍 Usage Examples

### Using the Python API

```python
from usac_velodata import USACyclingClient

# Initialize client
client = USACyclingClient()

# Get events for a state and year
events = client.get_events(state="CO", year=2023)

# Get details for an event by permit number
event_details = client.get_event_details(permit="2020-26")

# Get race results for a specific permit
all_result = client.get_complete_event_data(permit="2020-26", include_results=True) 

# Get race results for a specific permit
race_results = client.get_race_results(race_id="1337864")

# Fetch a flyer for an event
flyer = client.fetch_flyer(permit="2023-123", storage_dir="./flyers")

# Fetch multiple flyers in batch - Download for all states
flyers_stats = client.fetch_flyers_batch(
    start_year=2020, 
    end_year=2020, 
    limit=100,
    storage_dir="./flyers"
)

# List stored flyers
flyer_list = client.list_flyers(storage_dir="./flyers")

# Export to JSON
json_data = race_results.json()

# Export to CSV
with open("results.csv", "w") as f:
    f.write(race_results.to_csv())
    
# Configure caching
client = USACyclingClient(
    cache_enabled=True,
    cache_dir="./data/cache",
    cache_expiry=86400  # 24 hours
)

# Using rate limiting
client = USACyclingClient(
    rate_limit=10,  # Max 10 requests per minute
    backoff_factor=2.0  # Exponential backoff factor for retries
)
```

### Using the Command-Line Interface

The package includes a command-line interface for quick access to data:

```bash
# Get events for a state
usac_velodata events --state CA --year 2023 --output json

# Get race results for a permit
usac_velodata results --permit 2023-123 --output csv

# Fetch a flyer for an event
usac_velodata fetch-flyer --permit 2023-123 --storage-dir ./flyers

# Fetch multiple flyers in batch
usac_velodata fetch-flyers --start-year 2022 --end-year 2023 --limit 100 --storage-dir ./flyers

# List stored flyers
usac_velodata list-flyers --storage-dir ./flyers --output json --pretty
```

### Detailed CLI Usage

The `usac_velodata` package can be used directly from the command line:

```bash
python -m usac_velodata [command] [options]
```

Available commands:

- `events`: Fetch events by state and year
- `details`: Get detailed information about a specific event
- `disciplines`: List available disciplines
- `categories`: List available race categories
- `results`: Get race results for a specific event
- `complete`: Get complete event information including results
- `fetch-flyer`: Fetch a flyer for a specific event
- `fetch-flyers`: Fetch multiple flyers in batch
- `list-flyers`: List stored flyers

#### Global Options

- `--version`: Show the version and exit
- `--cache-dir PATH`: Directory to store cached data
- `--no-cache`: Disable caching of results
- `--log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}`: Set logging level

#### Events Command

```bash
python -m usac_velodata events --state CA [--year 2023] [--output {json,csv}] [--pretty]
```

- `--state`: Two-letter state code (required)
- `--year`: Year to search (defaults to current year)
- `--output`: Output format (json or csv)
- `--pretty`: Pretty-print JSON output

#### Results Command

```bash
# Using race ID (detailed results for a specific race)
python -m usac_velodata results --race-id 1337864 [--output {json,csv}] [--pretty]

# Using permit (returns event details)
python -m usac_velodata results --permit 2023-123 [--output {json,csv}] [--pretty]
```

#### Flyer Commands

```bash
# Fetch a flyer for a specific event
python -m usac_velodata fetch-flyer --permit 2023-123 --storage-dir ./flyers [--use-s3] [--s3-bucket my-bucket]

# Fetch multiple flyers in batch
python -m usac_velodata fetch-flyers --start-year 2022 --end-year 2023 [--limit 100] [--delay 5] --storage-dir ./flyers

# List stored flyers
python -m usac_velodata list-flyers --storage-dir ./flyers [--output {json,csv}] [--pretty]
```

#### Complete Command

```bash
python -m usac_velodata complete --permit 2023-123 [--no-results] [--output {json,csv}] [--pretty]
```

- `--permit`: Event permit number (required)
- `--no-results`: Don't include race results
- `--output`: Output format (json or csv)
- `--pretty`: Pretty-print JSON output

> Note: If complete data cannot be fetched (due to network or parsing issues), the command will automatically fall back to returning basic event details.

#### Examples

```bash
# Get events in California for 2023 in CSV format
python -m usac_velodata events --state CA --year 2023 --output csv

# Get detailed information about an event with pretty-printed JSON
python -m usac_velodata details --permit 2023-123 --pretty

# Get race results with caching disabled
python -m usac_velodata results --permit 2023-123 --output json --no-cache

# Get complete event information with debug logging
python -m usac_velodata complete --permit 2023-123 --log-level DEBUG

# Fetch a flyer and store it in S3
python -m usac_velodata fetch-flyer --permit 2023-123 --use-s3 --s3-bucket my-bucket

# Fetch multiple flyers with a 5-second delay between requests
python -m usac_velodata fetch-flyers --start-year 2023 --end-year 2023 --delay 5 --storage-dir ./flyers

# List stored flyers in JSON format
python -m usac_velodata list-flyers --storage-dir ./flyers --output json --pretty
```

## 📘 API Reference

### Client

```python
USACyclingClient(
    cache_enabled: bool = True,
    cache_dir: Optional[str] = None,
    cache_expiry: int = 86400,
    rate_limit: int = 10,
    backoff_factor: float = 1.0,
    logger: Optional[logging.Logger] = None
)
```

### Methods

| Method | Description |
|--------|-------------|
| `get_events(state, year)` | Get events for a state and year |
| `get_event_details(permit)` | Get details for an event by permit number |
| `get_race_results(permit)` | Get race results for a permit |
| `fetch_flyer(permit, storage_dir, use_s3)` | Fetch a flyer for an event |
| `fetch_flyers_batch(start_year, end_year, limit, storage_dir)` | Fetch multiple flyers in batch |
| `list_flyers(storage_dir)` | List stored flyers |

### Models

- `Event`: Represents a cycling event
- `RaceCategory`: Represents a race category
- `Rider`: Represents a race participant
- `RaceResult`: Represents race results

## 🏗️ Architecture

The package is structured around these main components:

- **Client**: Main interface for users, coordinates the workflow
- **Parsers**: Extract structured data from HTML and JSON responses
- **Models**: Pydantic models for type-validated data structures
- **Utils**: Helper functions for caching, logging, and rate limiting

## 🛠️ Development

### Setup Development Environment

```bash
pip install -e ".[dev]"
```

### Running Tests

```bash
pytest
```

### Code Style

This project uses Black, isort, and flake8 for code formatting and linting:

```bash
# Format code
black usac_velodata tests
isort usac_velodata tests

# Check code style
flake8 usac_velodata tests
mypy usac_velodata
```

## ❓ Troubleshooting

### Common Issues

- **Rate Limiting**: If you encounter "429 Too Many Requests" errors, reduce your rate_limit setting
- **Parsing Errors**: HTML structure may change; check for updates or submit an issue
- **Missing Results**: Some events may not have results published yet
- **S3 Storage**: Make sure boto3 is installed and AWS credentials are configured if using S3 storage

### Logging

Enable detailed logging for troubleshooting:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

client = USACyclingClient()
```

## 👥 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.


python -m unittest discover -v
