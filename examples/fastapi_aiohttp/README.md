# FastAPI + aiohttp Example

Complete example of Timetracer with FastAPI and aiohttp (async HTTP client).

## Quick Start

### 1. Install

```bash
pip install timetracer[fastapi,aiohttp]
```

### 2. Run in Record Mode

```bash
cd examples/fastapi_aiohttp
TIMETRACER_MODE=record uvicorn app:app --reload
```

### 3. Make Requests

```bash
# Health check
curl http://localhost:8000/

# Fetch external data (aiohttp call recorded)
curl http://localhost:8000/fetch-data

# Submit data (aiohttp POST recorded)
curl -X POST http://localhost:8000/submit

# Multiple calls in one request
curl -X POST http://localhost:8000/multi-call
```

Check `./cassettes/` for saved recordings.

### 4. Replay

```bash
# Replay with mocked aiohttp calls
TIMETRACER_MODE=replay \
TIMETRACER_CASSETTE=./cassettes/GET__fetch-data__abc123.json \
uvicorn app:app

# Make the same request - no network!
curl http://localhost:8000/fetch-data
```

## Files

| File | Description |
|------|-------------|
| `app.py` | FastAPI app with aiohttp calls |
| `test_app.py` | Integration tests |
| `cassettes/` | Saved recordings |

## What aiohttp Plugin Captures

- Request method, URL, headers
- Request body (json, data params)
- Response status, headers, body
- Timing information
- Errors and exceptions

## Run Tests

```bash
pytest test_app.py -v
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TIMETRACER_MODE` | off | `record`, `replay`, or `off` |
| `TIMETRACER_DIR` | ./cassettes | Where to save cassettes |
| `TIMETRACER_CASSETTE` | - | Cassette file for replay |
