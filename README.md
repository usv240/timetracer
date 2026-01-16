# Timetracer

**Time-travel debugging for FastAPI and Flask** - Record API requests, replay with mocked dependencies.

[![CI](https://github.com/usv240/timetracer/actions/workflows/ci.yml/badge.svg)](https://github.com/usv240/timetracer/actions)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PyPI](https://img.shields.io/pypi/v/timetracer.svg)](https://pypi.org/project/timetracer/)

---

## What is it?

Timetracer records real API request executions into portable **cassettes** and replays them locally by mocking dependency calls (HTTP, database, Redis).

*Record once. Replay anywhere. Debug faster.*

**Use cases:**
- Reproduce production/staging bugs quickly
- Build regression tests from real traffic
- Run offline demos
- Detect performance regressions
- Diff behavior between runs

## Installation

```bash
# Core + all plugins
pip install timetracer[all]

# Or just what you need
pip install timetracer[fastapi,httpx]      # FastAPI + HTTP
pip install timetracer[flask,httpx]        # Flask + HTTP
pip install timetracer[sqlalchemy]         # Database
pip install timetracer[redis]              # Redis
pip install timetracer[s3]                 # S3 storage
```

## Quickstart (3 Steps)

### Step 1: Install

```bash
pip install timetracer[fastapi,httpx]
```

### Step 2: Add 4 Lines to Your App

```python
from fastapi import FastAPI
from timetracer.config import TraceConfig
from timetracer.integrations.fastapi import TimeTraceMiddleware
from timetracer.plugins import enable_httpx

app = FastAPI()

# Add these 2 lines to enable Timetracer
config = TraceConfig.from_env()
app.add_middleware(TimeTraceMiddleware, config=config)

# Optional: Enable httpx tracking
enable_httpx()

@app.post("/checkout")
async def checkout():
    async with httpx.AsyncClient() as client:
        response = await client.get("https://api.example.com/data")
    return {"status": "ok"}
```

### Step 3: Record and Replay

```bash
# Record requests
TIMETRACER_MODE=record uvicorn app:app
curl -X POST http://localhost:8000/checkout

# Check cassettes
ls ./cassettes/
# Output: 2026-01-16/POST__checkout__abc123.json

# Replay (mocked HTTP calls)
TIMETRACER_MODE=replay \
  TIMETRACER_CASSETTE=./cassettes/2026-01-16/POST__checkout__abc123.json \
  uvicorn app:app
```

**Example Output:**

```
# Recording
TIMETRACER [OK] recorded POST /checkout  id=abc123  status=200  total=523ms  deps=http.client:1
  cassette: ./cassettes/2026-01-16/POST__checkout__abc123.json

# Replaying
TIMETRACER replay POST /checkout  mocked=1  matched=OK  runtime=45ms  recorded=523ms
```

That's it! External HTTP calls are now mocked from the recorded cassette.

---

## Flask Integration

```python
from flask import Flask
from timetracer.integrations.flask import init_app
from timetracer.config import TraceConfig

app = Flask(__name__)
init_app(app, TraceConfig.from_env())
```

## Features

### Frameworks
- **FastAPI** - Full middleware support
- **Flask** - WSGI middleware support

### Plugins
- **httpx** - Async/sync HTTP client
- **requests** - requests library
- **SQLAlchemy** - Database queries
- **Redis** - Redis commands

### Storage
- **Local filesystem** - Default
- **S3** - AWS S3 and S3-compatible (MinIO)

### Analysis and Tools
- **Diff engine** - Compare cassettes
- **HTML timeline** - Visualize execution
- **Hybrid replay** - Mock some deps, keep others live
- **Search and Index** - Find cassettes by endpoint, status, date

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `TIMETRACER_MODE` | `off`, `record`, `replay` | `off` |
| `TIMETRACER_DIR` | Cassette directory | `./cassettes` |
| `TIMETRACER_CASSETTE` | Replay cassette path | - |
| `TIMETRACER_SAMPLE_RATE` | Record fraction (0-1) | `1.0` |
| `TIMETRACER_ERRORS_ONLY` | Only record errors | `false` |
| `TIMETRACER_MOCK_PLUGINS` | Plugins to mock | all |
| `TIMETRACER_LIVE_PLUGINS` | Plugins to keep live | none |

## CLI

```bash
# List cassettes
timetracer list --dir ./cassettes

# Show cassette details
timetracer show ./cassettes/.../POST__checkout.json --events

# Diff two cassettes
timetracer diff --a cassette1.json --b cassette2.json

# Generate timeline
timetracer timeline ./cassettes/POST__checkout.json --open

# Search cassettes
timetracer search --endpoint /checkout --method POST --errors
timetracer index --dir ./cassettes

# S3 operations
timetracer s3 upload ./cassettes/ -b my-bucket
timetracer s3 sync up -d ./cassettes -b my-bucket
```

## Security

By default, Timetracer:
- Removes `Authorization`, `Cookie`, `Set-Cookie` headers
- Masks sensitive body keys (`password`, `token`, etc.)
- Captures bodies only on errors by default
- Enforces size limits (64KB default)

## Documentation

- [Quickstart](docs/quickstart.md)
- [Configuration](docs/configuration.md)
- [Plugins](docs/plugins.md)
- [Flask Integration](docs/flask.md)
- [SQLAlchemy Plugin](docs/sqlalchemy.md)
- [S3 Storage](docs/s3-storage.md)
- [Security](docs/security.md)

## Roadmap

- [x] v0.1-v0.3: Core, FastAPI, httpx, requests, diff, timeline
- [x] v1.0: Hybrid replay, schema v1.0, CI/CD, docs
- [x] v2.0: SQLAlchemy, Redis, Flask, S3 store
- [x] v2.1: Cassette search/index

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT - see [LICENSE](LICENSE).
