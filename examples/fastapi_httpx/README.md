# FastAPI + httpx Example

Complete example of Timetracer with FastAPI and httpx.

## What This Shows

- Recording API requests to cassettes
- Replaying with mocked external calls
- Using the CLI to inspect cassettes

## Quick Start

### 1. Install

```bash
pip install timetracer[fastapi,httpx]
```

### 2. Run in Record Mode

```bash
cd examples/fastapi_httpx
TIMETRACER_MODE=record uvicorn app:app --reload
```

### 3. Make Requests

```bash
# Health check
curl http://localhost:8000/

# External API call (recorded)
curl -X POST http://localhost:8000/checkout

# With path parameter
curl http://localhost:8000/user/123
```

Check `./cassettes/` for saved recordings.

### 4. Replay

```bash
# List cassettes
timetracer list --dir ./cassettes

# Replay a cassette
TIMETRACER_MODE=replay \
TIMETRACER_CASSETTE=./cassettes/POST__checkout__abc123.json \
uvicorn app:app --reload

# Make the same request - external calls are mocked!
curl -X POST http://localhost:8000/checkout
```

## Files

| File | Description |
|------|-------------|
| `app.py` | FastAPI app with httpx calls |
| `test_integration.py` | Integration tests |
| `cassettes/` | Saved recordings |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TIMETRACER_MODE` | off | `record`, `replay`, or `off` |
| `TIMETRACER_DIR` | ./cassettes | Where to save cassettes |
| `TIMETRACER_CASSETTE` | - | Cassette file for replay |
| `TIMETRACER_SAMPLE_RATE` | 1.0 | Record only X% of requests |

## Run Tests

```bash
pytest test_integration.py -v
```
