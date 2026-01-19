# pytest Plugin Example

Demonstrates Timetracer's pytest fixtures for cassette-based testing.

## Files

- `app.py` - FastAPI app with external HTTP calls
- `test_with_fixtures.py` - Tests using Timetracer fixtures

## Quick Start

### 1. Install

```bash
pip install timetracer[fastapi,httpx]
```

The pytest plugin auto-registers - no setup needed.

### 2. Use Fixtures in Tests

```python
# test_my_api.py

def test_replay_from_cassette(timetracer_replay, client):
    """Replay external calls from a recorded cassette."""
    with timetracer_replay("my_cassette.json"):
        response = client.get("/api/data")
        assert response.status_code == 200

def test_record_new_cassette(timetracer_record, client):
    """Record a new cassette during the test."""
    with timetracer_record("new_test.json"):
        response = client.get("/api/data")
    # Cassette saved after test completes

def test_auto_mode(timetracer_auto, client):
    """Auto-record first time, replay after."""
    with timetracer_auto("my_test.json"):
        response = client.get("/api/data")
```

### 3. Run Tests

```bash
cd examples/pytest_example
pytest test_with_fixtures.py -v
```

## Available Fixtures

| Fixture | Purpose |
|---------|---------|
| `timetracer_replay` | Replay from existing cassette |
| `timetracer_record` | Record new cassette |
| `timetracer_auto` | Record if missing, replay if exists |
| `timetracer_cassette_dir` | Get cassette directory path |

## Workflow

1. **First run**: Use `timetracer_record` or `timetracer_auto` to capture real API calls
2. **Commit cassettes**: Save to version control
3. **CI runs**: Tests replay from cassettes, no external dependencies
4. **Update**: Delete cassettes to re-record when APIs change

## Specifying Plugins

```python
def test_with_aiohttp(timetracer_replay, client):
    with timetracer_replay("test.json", plugins=["aiohttp", "requests"]):
        # Only specified plugins are mocked
        response = client.get("/api/async-data")
```

## Example Output

```
$ pytest test_with_fixtures.py -v

test_with_fixtures.py::TestBasicEndpoints::test_health_check PASSED
test_with_fixtures.py::TestReplayFixture::test_replay_fixture_works PASSED
test_with_fixtures.py::TestRecordFixture::test_record_creates_session PASSED
...
```
