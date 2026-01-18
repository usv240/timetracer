# Timetracer Quick Start

Get up and running in under 5 minutes.

## Installation

```bash
pip install timetracer[fastapi,httpx]    # with httpx
# or
pip install timetracer[fastapi,aiohttp]  # with aiohttp
```

## FastAPI Setup

```python
from fastapi import FastAPI
from timetracer.integrations.fastapi import auto_setup

app = auto_setup(FastAPI())

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    import httpx
    async with httpx.AsyncClient() as client:
        return (await client.get(f"https://api.example.com/users/{user_id}")).json()
```

## Flask Setup

```bash
pip install timetracer[flask,requests]
```

```python
from flask import Flask
from timetracer.integrations.flask import auto_setup

app = auto_setup(Flask(__name__))
```

---

## Recording Requests

Start your app in record mode:

```bash
TIMETRACER_MODE=record uvicorn app:app
curl http://localhost:8000/users/123
```

You should see output similar to:

```
timetracer [OK] recorded GET /users/123  id=a91c  status=200  total=412ms  deps=http.client:1
  cassette: ./cassettes/2026-01-16/GET__users_{user_id}__a91c.json
```

## Replaying Requests

Start your app in replay mode with a cassette file:

```bash
TIMETRACER_MODE=replay \
  TIMETRACER_CASSETTE=./cassettes/2026-01-16/GET__users_{user_id}__a91c.json \
  uvicorn app:app
```

All external HTTP calls are now served from the recorded cassette.

---

## Manual Setup

For more control over configuration:

```python
from fastapi import FastAPI
from timetracer import TraceConfig
from timetracer.integrations.fastapi import TimeTracerMiddleware
from timetracer.plugins import enable_httpx, enable_redis

app = FastAPI()
app.add_middleware(TimeTracerMiddleware, config=TraceConfig.from_env())
enable_httpx()
enable_redis()
```

---

## Environment Variables

| Variable | Default |
|----------|---------|
| `TIMETRACER_MODE` | `off` |
| `TIMETRACER_DIR` | `./cassettes` |
| `TIMETRACER_CASSETTE` | — |
| `TIMETRACER_SAMPLE_RATE` | `1.0` |
| `TIMETRACER_ERRORS_ONLY` | `false` |

---

## CLI Commands

```bash
timetracer list --dir ./cassettes
timetracer show ./cassettes/GET__users.json --events
timetracer timeline ./cassettes/GET__users.json --open
timetracer dashboard --open  # Open interactive dashboard
```

---

## Next Steps

- [Configuration Reference](configuration.md)
- [Plugin Guide](plugins.md)
- [Security Best Practices](security.md)
