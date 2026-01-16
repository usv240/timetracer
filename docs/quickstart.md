# Timetrace Quickstart

Get started with Timetrace in under 5 minutes.

## Installation

```bash
pip install timetrace
```

For httpx capturing (recommended):
```bash
pip install timetrace[httpx]
```

For requests library support:
```bash
pip install timetrace requests
```

## Basic Usage with FastAPI

### 1. Add the Middleware

```python
from fastapi import FastAPI
from timetrace.integrations.fastapi import TimeTraceMiddleware
from timetrace.config import TraceConfig
from timetrace.plugins.httpx_plugin import enable_httpx

app = FastAPI()

# Configure timetrace
config = TraceConfig(
    mode="record",
    cassette_dir="./cassettes",
    capture=["http"],
)

# Add middleware
app.add_middleware(TimeTraceMiddleware, config=config)

# Enable httpx capturing
enable_httpx()
```

### 2. Record Your First Request

Run your app and make a request:

```bash
TIMETRACE_MODE=record uvicorn app:app --reload
curl http://localhost:8000/your-endpoint
```

You'll see output like:
```
TIMETRACE [OK] recorded GET /your-endpoint  id=a91c  status=200  total=412ms  deps=http.client:1
  cassette: cassettes/2026-01-15/GET__your-endpoint__a91c.json
```

### 3. Replay with Mocked Dependencies

```bash
TIMETRACE_MODE=replay \
TIMETRACE_CASSETTE=cassettes/2026-01-15/GET__your-endpoint__a91c.json \
uvicorn app:app
```

Now all external HTTP calls are mocked from the recorded cassette.

## Environment Variable Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `TIMETRACE_MODE` | `off`, `record`, or `replay` | `off` |
| `TIMETRACE_DIR` | Cassette storage directory | `./cassettes` |
| `TIMETRACE_CASSETTE` | Specific cassette path (for replay) | - |
| `TIMETRACE_SAMPLE_RATE` | Recording sample rate (0.0-1.0) | `1.0` |
| `TIMETRACE_ERRORS_ONLY` | Only record error responses | `false` |
| `TIMETRACE_EXCLUDE_PATHS` | Comma-separated paths to skip | `/health,/metrics` |

## CLI Commands

### List cassettes
```bash
timetrace list --dir ./cassettes --limit 20
```

### Show cassette details
```bash
timetrace show ./cassettes/2026-01-15/GET__checkout__a91c.json
```

### Generate HTML timeline
```bash
timetrace timeline ./cassettes/GET__checkout__a91c.json --open
```

### Diff two cassettes
```bash
timetrace diff --a cassette1.json --b cassette2.json
```

## Next Steps

- Read [Configuration](configuration.md) for all options
- Learn about [Plugins](plugins.md) and hybrid replay
- Review [Security](security.md) for redaction settings
