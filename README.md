# Timetracer

**Time-travel debugging for FastAPI and Flask** — Record API requests, replay with mocked dependencies.

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
pip install timetracer[fastapi,httpx]    # FastAPI + HTTP
pip install timetracer[flask,requests]   # Flask + HTTP
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
from timetracer.integrations.fastapi import TimeTraceMiddleware
from timetracer.plugins import enable_httpx

app = FastAPI()

config = TraceConfig(
    mode="record",
    cassette_dir="./my-cassettes",
    errors_only=True,
)
app.add_middleware(TimeTraceMiddleware, config=config)

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
| `TIMETRACER_MOCK_PLUGINS` | Plugins to mock during replay | all |
| `TIMETRACER_LIVE_PLUGINS` | Plugins to keep live during replay | none |

---

## Features

| Category | Supported |
|----------|-----------|
| **Frameworks** | FastAPI, Flask |
| **HTTP Clients** | httpx, requests |
| **Databases** | SQLAlchemy |
| **Cache** | Redis |
| **Storage** | Local filesystem, AWS S3 |
| **Tools** | CLI, diff engine, HTML timeline |

---

## CLI

```bash
timetracer list --dir ./cassettes              # List all cassettes
timetracer show ./cassettes/GET__users.json    # Show cassette details
timetracer diff --a old.json --b new.json      # Compare two cassettes
timetracer timeline ./cassettes/GET__users.json --open  # Generate timeline
```

---

## Security

Timetracer automatically protects sensitive data:

- Removes `Authorization`, `Cookie`, and `Set-Cookie` headers
- Masks sensitive fields like `password`, `token`, `api_key` in request/response bodies
- Enforces a 64KB body size limit to prevent large data captures

---

## Documentation

- [Quick Start Guide](docs/quickstart.md)
- [Configuration Reference](docs/configuration.md)
- [Plugin Guide](docs/plugins.md)
- [Flask Integration](docs/flask.md)
- [Security Best Practices](docs/security.md)

---

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License. See [LICENSE](LICENSE) for details.
