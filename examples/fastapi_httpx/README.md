# Timetracer FastAPI + httpx Example

This example demonstrates using Timetracer to record and replay API calls.

## Setup

```bash
# From the Timetracer root directory
cd examples/fastapi_httpx

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# or: source venv/bin/activate  # Unix

# Install dependencies
pip install -e "../../[all]"
pip install uvicorn
```

## Record Mode

Record real API calls to cassettes:

```bash
# Start server in record mode
$env:TimetracerR_MODE="record"; uvicorn app:app --reload

# Or on Unix:
# TimetracerR_MODE=record uvicorn app:app --reload
```

Make some requests:

```bash
# Simple endpoint
curl http://localhost:8000/

# Endpoint with external API call
curl -X POST http://localhost:8000/checkout

# Endpoint with path parameter
curl http://localhost:8000/user/123

# Multiple external calls
curl -X POST http://localhost:8000/payment
```

Check the terminal for recording output and look in `./cassettes/` for saved cassettes.

## Replay Mode

Replay using recorded cassettes (no network calls):

```bash
# Find a cassette
Timetracer list --dir ./cassettes

# Start server in replay mode
$env:TimetracerR_MODE="replay"
$env:TimetracerR_CASSETTE="./cassettes/2026-01-15/POST__checkout__abcd1234.json"
uvicorn app:app --reload

# Make the same request - external calls are mocked!
curl -X POST http://localhost:8000/checkout
```

## Inspect Cassettes

Use the CLI to inspect recorded cassettes:

```bash
# List recent cassettes
Timetracer list --dir ./cassettes

# Show cassette summary
Timetracer show ./cassettes/2026-01-15/POST__checkout__abcd1234.json

# Show with event details
Timetracer show ./cassettes/2026-01-15/POST__checkout__abcd1234.json --events
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `TimetracerR_MODE` | `off`, `record`, or `replay` |
| `TimetracerR_DIR` | Cassette output directory |
| `TimetracerR_CASSETTE` | Specific cassette for replay |
| `TimetracerR_SAMPLE_RATE` | 0.0-1.0, fraction of requests to record |
| `TimetracerR_ERRORS_ONLY` | `true` to only record error responses |
