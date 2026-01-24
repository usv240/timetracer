# Starlette Example

This example demonstrates Timetracer integration with Starlette, the lightweight ASGI framework that powers FastAPI.

## What This Example Shows

- Starlette integration using `auto_setup()` helper
- HTTP client tracking with httpx (GitHub API calls)
- Path parameters in dynamic routes
- Multiple external API calls in single request
- Record and replay functionality

## Installation

Install required dependencies:

```bash
pip install timetracer starlette httpx

# Or from project root
pip install -e ".[starlette]"
```

## Running the Example

### Record Mode

Record all external API calls:

```bash
# Run demo
TIMETRACER_MODE=record python app.py

# Or with uvicorn
TIMETRACER_MODE=record uvicorn app:app --reload
```

Make requests to the application:
```bash
curl http://localhost:8000/
curl http://localhost:8000/user/octocat
curl http://localhost:8000/repos/octocat
curl http://localhost:8000/weather/London
```

Cassettes are saved to `./cassettes/`.

### Replay Mode

Replay using a recorded cassette:

```bash
TIMETRACER_MODE=replay \
TIMETRACER_CASSETTE=./cassettes/2026-01-22/GET__user_octocat__abc123.json \
python app.py
```

All external API calls are mocked using recorded responses.

## Endpoints

| Endpoint | Description | External Calls |
|----------|-------------|----------------|
| `GET /` | Homepage | None |
| `GET /user/{username}` | Get GitHub user info | 1 (GitHub API) |
| `GET /repos/{username}` | Get user's top repos | 2 (GitHub API) |
| `GET /weather/{city}` | Get current weather | 1 (wttr.in API) |

## Example Output

### Record Mode

```
============================================================
Starlette + Timetracer Demo
============================================================

Mode: record
Cassette dir: ./cassettes

Testing endpoints...

1. GET / (homepage)
   Status: 200
   Message: Welcome to the Starlette + Timetracer example!

timetracer [OK] recorded GET /  id=a1b2  status=200  total=12ms  deps=none

2. GET /user/octocat (GitHub API)
   Status: 200
   Username: octocat
   Name: The Octocat
   Repos: 8

timetracer [OK] recorded GET /user/octocat  id=c3d4  status=200  total=245ms  deps=http.client:1
  cassette: cassettes/2026-01-22/GET__user_octocat__c3d4.json

3. GET /repos/octocat (GitHub API - multiple calls)
   Status: 200
   Total repos: 8
   Top repo: Hello-World

timetracer [OK] recorded GET /repos/octocat  id=e5f6  status=200  total=412ms  deps=http.client:2
  cassette: cassettes/2026-01-22/GET__repos_octocat__e5f6.json

============================================================
Recorded 3 cassettes:
  - GET____a1b2.json (1,234 bytes)
  - GET__user_octocat__c3d4.json (3,456 bytes)
  - GET__repos_octocat__e5f6.json (5,678 bytes)

To replay, run:
  TIMETRACER_MODE=replay TIMETRACER_CASSETTE=cassettes/2026-01-22/GET____a1b2.json python app.py

Done!
```

### Replay Mode

```
timetracer replay GET /user/octocat  mocked=1  matched=OK  runtime=8ms  recorded=245ms
```

Notice the runtime is 8ms instead of 245ms because no actual API call was made.

## What Gets Recorded

Each cassette contains:

1. **Request Details**
   - Method, path, headers, query parameters
   - Request body (if present)
   - Route template

2. **Response Details**
   - Status code, headers, body
   - Duration

3. **Dependency Events**
   - All httpx calls with request/response data
   - Timing information
   - Signatures for matching during replay

## Testing

Run tests for this example:

```bash
pytest test_starlette_example.py -v
```

## Key Features

### Auto Setup

One-line configuration:

```python
from timetracer.integrations.starlette import auto_setup

auto_setup(app, plugins=["httpx"])
```

This configures:
- Timetracer middleware
- httpx plugin
- Environment-based configuration

### Async Support

Starlette is fully async, and Timetracer handles it seamlessly:

```python
async def get_user(request):
    async with httpx.AsyncClient() as client:
        response = await client.get("https://api.github.com/users/octocat")
        # This call is recorded
```

### Time Travel Debugging

Common workflow:

1. Record failing request in production
2. Download the cassette
3. Replay locally with exact same conditions
4. Debug without accessing external APIs

## Configuration Options

### Environment Variables

```bash
TIMETRACER_MODE=record              # record, replay, or off
TIMETRACER_DIR=./cassettes          # Cassette storage directory
TIMETRACER_CASSETTE=path/to/file    # Cassette for replay mode
TIMETRACER_SAMPLE_RATE=0.1          # Record 10% of requests
TIMETRACER_ERRORS_ONLY=true         # Only record errors
TIMETRACER_COMPRESSION=gzip         # Compress cassettes
```

### Programmatic Configuration

```python
from timetracer.config import TraceConfig

config = TraceConfig(
    mode="record",
    cassette_dir="./my-cassettes",
    exclude_paths=["/health", "/metrics"],
    sample_rate=1.0,
)

auto_setup(app, config=config, plugins=["httpx"])
```

## Troubleshooting

### httpx calls not being recorded

Verify the plugin is enabled:
```python
from timetracer.plugins import enable_httpx
enable_httpx()
```

Or use `auto_setup()` which enables it automatically:
```python
auto_setup(app, plugins=["httpx"])
```

### Cassettes not saving

Check that mode is set to record:
```bash
echo $TIMETRACER_MODE  # Should be "record"
```

## Learn More

- [Starlette Documentation](https://www.starlette.io/)
- [Timetracer Documentation](../../docs/)
- [FastAPI Integration](../fastapi_example/)
