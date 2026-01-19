# pytest Integration

Timetracer provides a pytest plugin for cassette-based testing.

## Installation

The plugin is included with Timetracer and auto-registered with pytest:

```bash
pip install timetracer
```

Verify it's loaded:

```bash
pytest --version
# Should show: plugins: timetracer-x.x.x
```

## Fixtures

### timetracer_replay

Replay recorded cassettes in your tests:

```python
def test_user_endpoint(timetracer_replay, client):
    with timetracer_replay("user_fetch.json"):
        response = client.get("/api/users/1")
        assert response.status_code == 200
        assert response.json()["name"] == "John"
```

All HTTP calls inside the context are mocked using the cassette.

### timetracer_record

Record new cassettes during test runs:

```python
def test_and_record(timetracer_record, client):
    with timetracer_record("new_cassette.json") as session:
        response = client.get("/api/users")
    
    # Cassette is saved after context exits
    assert len(session.events) > 0
```

### timetracer_auto

Automatically record on first run, replay on subsequent runs:

```python
def test_auto_mode(timetracer_auto, client):
    with timetracer_auto("my_test.json"):
        response = client.get("/api/users")
        assert response.status_code == 200
    
    # First run: records the cassette
    # Later runs: replays from cassette
```

### timetracer_cassette_dir

Get the cassette directory path:

```python
def test_cassette_location(timetracer_cassette_dir):
    assert timetracer_cassette_dir.exists()
    print(f"Cassettes stored in: {timetracer_cassette_dir}")
```

## Configuration

### Cassette Directory

Set the default cassette directory in pytest.ini or pyproject.toml:

```ini
# pytest.ini
[pytest]
timetracer_cassette_dir = tests/cassettes
```

```toml
# pyproject.toml
[tool.pytest.ini_options]
timetracer_cassette_dir = "tests/cassettes"
```

### Plugin Selection

Specify which plugins to enable:

```python
def test_with_aiohttp(timetracer_replay):
    with timetracer_replay("async_test.json", plugins=["aiohttp"]):
        # Only aiohttp calls are mocked
        pass
```

Available plugins: `httpx`, `requests`, `aiohttp`, `sqlalchemy`, `redis`

## Examples

### FastAPI Test

```python
from fastapi.testclient import TestClient
from myapp import app

client = TestClient(app)

def test_external_api_call(timetracer_replay):
    with timetracer_replay("external_call.json"):
        response = client.get("/fetch-from-external-api")
        assert response.status_code == 200
        # External API call is mocked, no network needed
```

### Django Test

```python
from django.test import Client

client = Client()

def test_django_view(timetracer_replay):
    with timetracer_replay("django_test.json"):
        response = client.get("/api/users/")
        assert response.status_code == 200
```

### Async Test

```python
import pytest

@pytest.mark.asyncio
async def test_async_endpoint(timetracer_replay, async_client):
    with timetracer_replay("async_test.json", plugins=["aiohttp"]):
        response = await async_client.get("/api/async-data")
        assert response.status_code == 200
```

## Workflow

1. **First run** - Use `timetracer_auto` or `timetracer_record` to capture real API calls
2. **Commit cassettes** - Save cassettes to version control
3. **CI runs** - Tests replay from cassettes, no external dependencies needed
4. **Update cassettes** - Delete old cassettes to re-record when APIs change

## Tips

### Organizing Cassettes

```
tests/
├── cassettes/
│   ├── test_users/
│   │   ├── test_get_user.json
│   │   └── test_create_user.json
│   └── test_orders/
│       └── test_checkout.json
├── test_users.py
└── test_orders.py
```

### Strict Mode

Enable strict mode to fail if cassette doesn't match:

```python
def test_strict_replay(timetracer_replay):
    with timetracer_replay("test.json", strict=True):
        # Fails if any unmatched events
        response = client.get("/api/users")
```

### Inspecting Sessions

Access the session object for debugging:

```python
def test_inspect_session(timetracer_record):
    with timetracer_record() as session:
        client.get("/api/users")
    
    print(f"Recorded {len(session.events)} events")
    for event in session.events:
        print(f"  - {event.event_type}: {event.signature}")
```
