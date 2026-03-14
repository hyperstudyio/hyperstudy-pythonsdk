# hyperstudy

Python SDK for the [HyperStudy](https://hyperstudy.io) experiment platform API. Designed for researchers working in Jupyter, marimo, or Python scripts.

## Installation

```bash
pip install hyperstudy
```

For polars support:

```bash
pip install hyperstudy[polars]
```

## Quick Start

```python
import hyperstudy

hs = hyperstudy.HyperStudy(api_key="hst_live_...")
# Or set the HYPERSTUDY_API_KEY environment variable

# Fetch events as a pandas DataFrame
events = hs.get_events("your_experiment_id")

# Room-scoped data
events = hs.get_events("room_id", scope="room")

# Participant-scoped data
events = hs.get_events("participant_id", scope="participant", room_id="room_id")
```

## Data Types

All data retrieval methods follow the same pattern:

```python
events      = hs.get_events("exp_id")
recordings  = hs.get_recordings("exp_id")
chat        = hs.get_chat("exp_id")
videochat   = hs.get_videochat("exp_id")
sync        = hs.get_sync("exp_id")
ratings     = hs.get_ratings("exp_id", kind="continuous")
components  = hs.get_components("exp_id")
participants = hs.get_participants("exp_id")
rooms       = hs.get_rooms("exp_id")
```

### Output Formats

```python
df_pandas = hs.get_events("exp_id")                      # pandas (default)
df_polars = hs.get_events("exp_id", output="polars")     # polars
raw       = hs.get_events("exp_id", output="dict")       # list[dict]
```

### Filtering

```python
events = hs.get_events(
    "exp_id",
    start_time="2024-01-01T10:00:00Z",
    end_time="2024-01-01T12:00:00Z",
    category="component",
    sort="onset",
    limit=100,
)
```

### Auto-Pagination

When `limit` is not set, all pages are fetched automatically with a progress bar:

```python
all_events = hs.get_events("exp_id")  # fetches all pages
```

## Experiment Management

```python
# List experiments
experiments = hs.list_experiments()

# Get details (with rich display in notebooks)
exp = hs.get_experiment("exp_id")

# Create / update / delete
new_exp = hs.create_experiment(name="My Study", description="...")
hs.update_experiment("exp_id", name="Updated Name")
hs.delete_experiment("exp_id")
```

## All Data for a Participant

```python
data = hs.get_all_data("participant_id", room_id="room_id")
# Returns: {"events": DataFrame, "recordings": DataFrame, "chat": DataFrame, ...}
```

## API Key

Generate an API key from the HyperStudy dashboard under Settings. Keys follow the format `hst_{environment}_{key}` and are passed via the `X-API-Key` header.

## Documentation

Full documentation: [docs.hyperstudy.io/developers/python-sdk](https://docs.hyperstudy.io/developers/python-sdk)

## Development

```bash
git clone https://github.com/ljchang/hyperstudy-pythonsdk.git
cd hyperstudy-pythonsdk
pip install -e ".[dev,polars]"
pytest --cov=hyperstudy
ruff check src/
```

## License

MIT
