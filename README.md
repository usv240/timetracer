# Timetracer

**Time-travel debugging for FastAPI, Starlette, Flask, and Django** — Record API requests, replay with mocked dependencies.

[![CI](https://github.com/usv240/timetracer/actions/workflows/ci.yml/badge.svg)](https://github.com/usv240/timetracer/actions)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PyPI](https://img.shields.io/pypi/v/timetracer.svg)](https://pypi.org/project/timetracer/)

---

## What is Timetracer?

Timetracer captures real API requests into portable **cassettes** and replays them with mocked dependencies (HTTP calls, database queries, Redis commands).

> Record once. Replay anywhere. Debug faster.

**Common use cases:**

- Reproduce production bugs locally without access to external services
- Build regression tests from real traffic patterns
- Run demos offline with pre-recorded data
- Detect performance regressions between releases
- Compare behavior between different code versions

---

## How It Works

Timetracer acts as middleware that intercepts your app's external calls:

```
                      RECORD MODE
┌──────────┐      ┌──────────────┐      ┌──────────────┐
│  Client  │ ───► │   Your App   │ ───► │   External   │
│  (curl)  │      │ + Timetracer │      │   APIs/DB    │
└──────────┘      └──────────────┘      └──────────────┘
                         │
                         ▼
                   ┌───────────┐
                   │  Cassette │  (saves everything)
                   │   .json   │
                   └───────────┘


                      REPLAY MODE
┌──────────┐      ┌──────────────┐       ╳ External APIs
│  Client  │ ───► │   Your App   │       ╳ (not called)
│  (curl)  │      │ + Timetracer │
└──────────┘      └──────────────┘
                         ▲
                         │
                   ┌───────────┐
                   │  Cassette │  (replays from here)
                   │   .json   │
                   └───────────┘
```

---

## Installation

```bash
pip install timetracer[all]
```

Or install only what you need:

```bash
pip install timetracer[fastapi,httpx]    # FastAPI + httpx
pip install timetracer[starlette,httpx]  # Starlette + httpx
pip install timetracer[flask,requests]   # Flask + requests
pip install timetracer[django,requests]  # Django + requests
pip install timetracer[motor]            # Motor (MongoDB async) + PyMongo (sync)
```

---

## Quick Start

### FastAPI

```python
from fastapi import FastAPI
from timetracer.integrations.fastapi import auto_setup

app = auto_setup(FastAPI())

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    async with httpx.AsyncClient() as client:
        return (await client.get(f"https://api.example.com/users/{user_id}")).json()
```

### Starlette

```python
from starlette.applications import Starlette
from timetracer.integrations.starlette import auto_setup

app = auto_setup(Starlette(debug=True))
```

### Flask

```python
from flask import Flask
from timetracer.integrations.flask import auto_setup

app = auto_setup(Flask(__name__))
```

### Record and Replay

```bash
# Record mode - captures all external calls
TIMETRACER_MODE=record uvicorn app:app
curl http://localhost:8000/users/123

# Replay mode - mocks external calls from cassette
TIMETRACER_MODE=replay \
  TIMETRACER_CASSETTE=./cassettes/2026-01-16/GET__users_{user_id}__abc.json \
  uvicorn app:app
```

---

## Manual Setup

For more control over configuration:

```python
import httpx
from fastapi import FastAPI
from timetracer import TraceConfig
from timetracer.integrations.fastapi import TimeTracerMiddleware
from timetracer.plugins import enable_httpx

app = FastAPI()

config = TraceConfig(
    mode="record",
    cassette_dir="./my-cassettes",
    errors_only=True,
)
app.add_middleware(TimeTracerMiddleware, config=config)

enable_httpx()
```

---

## Configuration

All settings are controlled via environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `TIMETRACER_MODE` | `off`, `record`, `replay` | `off` |
| `TIMETRACER_DIR` | Cassette storage directory | `./cassettes` |
| `TIMETRACER_CASSETTE` | Path to cassette file (replay mode) | — |
| `TIMETRACER_SAMPLE_RATE` | Fraction of requests to record (0-1) | `1.0` |
| `TIMETRACER_ERRORS_ONLY` | Only record error responses | `false` |
| `TIMETRACER_COMPRESSION` | Cassette compression: `none`, `gzip` | `none` |
| `TIMETRACER_MOCK_PLUGINS` | Plugins to mock during replay | all |
| `TIMETRACER_LIVE_PLUGINS` | Plugins to keep live during replay | none |

---

## Features

| Category | Supported |
|----------|-----------|
| **Frameworks** | FastAPI, Starlette, Flask, Django |
| **HTTP Clients** | httpx, requests, aiohttp |
| **Databases** | SQLAlchemy, Motor (MongoDB async), PyMongo (MongoDB sync) |
| **Cache** | Redis |
| **Storage** | Local filesystem, AWS S3 |
| **Testing** | pytest plugin with fixtures |
| **Tools** | CLI, diff engine, HTML timeline, **Dashboard** |
| **Compression** | Gzip (60-95% size reduction) |

---

## CLI

```bash
timetracer list --dir ./cassettes              # List all cassettes
timetracer show ./cassettes/GET__users.json    # Show cassette details
timetracer diff --a old.json --b new.json      # Compare two cassettes
timetracer timeline ./cassettes/GET__users.json --open  # Generate timeline
timetracer dashboard --dir ./cassettes --open  # Generate interactive dashboard
timetracer serve --dir ./cassettes --open      # Start live dashboard with replay
```

---

## Dashboard

Browse and debug all recorded cassettes with the interactive dashboard:

```bash
# Static HTML dashboard (open in browser)
timetracer dashboard --dir ./cassettes --open

# Live dashboard with real-time replay
timetracer serve --dir ./cassettes --open
```

**Features:**
- **Sortable table** - Sort by time, method, status, duration
- **Filters** - Filter by method, status, duration, time range
- **Error highlighting** - Errors shown in red with warning icons
- **Stack traces** - View exception details and Python tracebacks
- **Replay** - One-click replay to see recorded request/response
- **Raw JSON** - Expandable view of full cassette data

---

## Security

Timetracer automatically protects sensitive data:

- Removes `Authorization`, `Cookie`, and `Set-Cookie` headers
- Masks sensitive fields like `password`, `token`, `api_key` in request/response bodies
- Enforces a 64KB body size limit to prevent large data captures

---

## Documentation

- [Changelog](CHANGELOG.md) - Version history and changes
- [Release Notes](RELEASE_NOTES.md) - Detailed release information
- [Why Timetracer?](docs/why-timetracer.md)
- [Quick Start Guide](docs/quickstart.md)
- [Configuration Reference](docs/configuration.md)
- [Dashboard Guide](docs/dashboard.md)
- [Plugin Guide](docs/plugins.md)
- [SQLAlchemy Integration](docs/sqlalchemy.md)
- [Motor (MongoDB) Integration](docs/motor.md)
- [PyMongo (MongoDB) Integration](docs/pymongo.md)
- [Starlette Integration](docs/starlette.md)
- [Flask Integration](docs/flask.md)
- [Django Integration](docs/django.md)
- [pytest Plugin](docs/pytest.md)
- [Cassette Compression](docs/compression.md)
- [S3 Storage](docs/s3-storage.md)
- [Cassette Search](docs/search.md)
- [Security Best Practices](docs/security.md)

---

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License. See [LICENSE](LICENSE) for details.
