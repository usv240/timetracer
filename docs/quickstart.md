# Timetracer Quickstart

Get started with Timetracer in under 5 minutes.

## Installation

```bash
pip install timetracer
```

For httpx capturing (recommended):
```bash
pip install timetracer[httpx]
```

For requests library support:
```bash
pip install timetracer requests
```

## Basic Usage with FastAPI

### 1. Add the Middleware

```python
from fastapi import FastAPI
from timetracer.integrations.fastapi import TimeTraceMiddleware
from timetracer.config import TraceConfig
from timetracer.plugins.httpx_plugin import enable_httpx

app = FastAPI()

# Configure timetracer
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
TIMETRACER_MODE=record uvicorn app:app --reload
curl http://localhost:8000/your-endpoint
```

You'll see output like:
```
TIMETRACER [OK] recorded GET /your-endpoint  id=a91c  status=200  total=412ms  deps=http.client:1
  cassette: cassettes/2026-01-16/GET__your-endpoint__a91c.json
```

### 3. Replay with Mocked Dependencies

```bash
TIMETRACER_MODE=replay \
TIMETRACER_CASSETTE=cassettes/2026-01-16/GET__your-endpoint__a91c.json \
uvicorn app:app
```

Now all external HTTP calls are mocked from the recorded cassette.

## Environment Variable Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `TIMETRACER_MODE` | `off`, `record`, or `replay` | `off` |
| `TIMETRACER_DIR` | Cassette storage directory | `./cassettes` |
| `TIMETRACER_CASSETTE` | Specific cassette path (for replay) | - |
| `TIMETRACER_SAMPLE_RATE` | Recording sample rate (0.0-1.0) | `1.0` |
| `TIMETRACER_ERRORS_ONLY` | Only record error responses | `false` |
| `TIMETRACER_EXCLUDE_PATHS` | Comma-separated paths to skip | `/health,/metrics` |

## CLI Commands

### List cassettes
```bash
timetracer list --dir ./cassettes --limit 20
```

### Show cassette details
```bash
timetracer show ./cassettes/2026-01-16/GET__checkout__a91c.json
```

### Generate HTML timeline
```bash
timetracer timeline ./cassettes/GET__checkout__a91c.json --open
```

### Diff two cassettes
```bash
timetracer diff --a cassette1.json --b cassette2.json
```

## Next Steps

- Read [Configuration](configuration.md) for all options
- Learn about [Plugins](plugins.md) and hybrid replay
- Review [Security](security.md) for redaction settings
