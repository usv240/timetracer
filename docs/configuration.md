# Timetrace Configuration Reference

Complete reference for all Timetrace configuration options.

## TraceConfig Options

### Core Settings

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `mode` | `TraceMode` | `off` | Operating mode: `off`, `record`, `replay` |
| `service_name` | `str` | `timetrace-service` | Name of your service |
| `env` | `str` | `local` | Environment name |

### Cassette Storage

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `cassette_dir` | `str` | `./cassettes` | Directory for cassette files |
| `cassette_path` | `str` | `None` | Specific cassette for replay mode |

### Capture Control

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `capture` | `list[str]` | `["http"]` | Plugins to enable |
| `sample_rate` | `float` | `1.0` | Recording sample rate (0.0-1.0) |
| `errors_only` | `bool` | `False` | Only record error responses |
| `exclude_paths` | `list[str]` | `/health,/metrics,/docs,/openapi.json` | Paths to skip |

### Body Capture Policies

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `max_body_kb` | `int` | `64` | Maximum body size to capture |
| `store_request_body` | `CapturePolicy` | `on_error` | When to store request body |
| `store_response_body` | `CapturePolicy` | `on_error` | When to store response body |

**CapturePolicy values:**
- `never` - Never store body
- `on_error` - Store only on error responses
- `always` - Always store body

### Replay Settings

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `strict_replay` | `bool` | `True` | Raise errors on mismatches |
| `mock_plugins` | `list[str]` | `[]` | Plugins to mock (empty = all) |
| `live_plugins` | `list[str]` | `[]` | Plugins to keep live |

### Logging

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `log_level` | `str` | `info` | Logging level |

## Environment Variables

All options can be set via environment variables with the `TIMETRACE_` prefix:

| Environment Variable | Config Option |
|---------------------|---------------|
| `TIMETRACE_MODE` | `mode` |
| `TIMETRACE_SERVICE` | `service_name` |
| `TIMETRACE_ENV` | `env` |
| `TIMETRACE_DIR` | `cassette_dir` |
| `TIMETRACE_CASSETTE` | `cassette_path` |
| `TIMETRACE_CAPTURE` | `capture` (comma-separated) |
| `TIMETRACE_SAMPLE_RATE` | `sample_rate` |
| `TIMETRACE_ERRORS_ONLY` | `errors_only` |
| `TIMETRACE_EXCLUDE_PATHS` | `exclude_paths` (comma-separated) |
| `TIMETRACE_MAX_BODY_KB` | `max_body_kb` |
| `TIMETRACE_STORE_REQ_BODY` | `store_request_body` |
| `TIMETRACE_STORE_RES_BODY` | `store_response_body` |
| `TIMETRACE_STRICT_REPLAY` | `strict_replay` |
| `TIMETRACE_MOCK_PLUGINS` | `mock_plugins` (comma-separated) |
| `TIMETRACE_LIVE_PLUGINS` | `live_plugins` (comma-separated) |
| `TIMETRACE_LOG_LEVEL` | `log_level` |

## Configuration Priority

1. Explicit constructor arguments (highest priority)
2. Environment variables
3. Default values (lowest priority)

## Examples

### Programmatic Configuration

```python
from timetrace.config import TraceConfig
from timetrace.constants import TraceMode, CapturePolicy

config = TraceConfig(
    mode=TraceMode.RECORD,
    service_name="my-api",
    cassette_dir="./recordings",
    sample_rate=0.1,  # Record 10% of requests
    errors_only=True,  # Only record errors
    store_response_body=CapturePolicy.ALWAYS,
    exclude_paths=["/health", "/metrics", "/internal/*"],
)
```

### Environment-Only Configuration

```bash
export TIMETRACE_MODE=record
export TIMETRACE_DIR=./cassettes
export TIMETRACE_SAMPLE_RATE=0.5
export TIMETRACE_ERRORS_ONLY=true
```

```python
from timetrace.config import TraceConfig
config = TraceConfig.from_env()
```

### Hybrid Configuration

```python
from timetrace.config import TraceConfig

# Set base config in code, allow env overrides
config = TraceConfig(
    service_name="my-api",
    cassette_dir="./cassettes",
).with_env_overrides()  # TIMETRACE_MODE env var will override mode
```

### Hybrid Replay Mode

Mock external APIs but keep database live:

```python
config = TraceConfig(
    mode="replay",
    cassette_path="./cassettes/checkout.json",
    mock_plugins=["http"],  # Only mock HTTP
    live_plugins=[],        # Or use live_plugins to exclude specific ones
)
```

Or via environment:
```bash
TIMETRACE_MODE=replay
TIMETRACE_CASSETTE=./cassettes/checkout.json
TIMETRACE_LIVE_PLUGINS=db,redis  # Keep DB and Redis live
```
