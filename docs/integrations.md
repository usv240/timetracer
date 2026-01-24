# Integration Guides

Step-by-step guides for integrating Timetracer with your framework.

---

## FastAPI

### 1. Install

```bash
pip install timetracer[fastapi,httpx]
```

### 2. Add Middleware

```python
# main.py
from fastapi import FastAPI
from timetracer.integrations.fastapi import TimeTracerMiddleware

app = FastAPI()
app.add_middleware(TimeTracerMiddleware)
```

### 3. Enable HTTP Client Plugin

```python
from timetracer.plugins import enable_httpx
enable_httpx()
```

### 4. Record

```bash
TIMETRACER_MODE=record uvicorn main:app --reload
```

Make some requests:
```bash
curl http://localhost:8000/your-endpoint
```

Check `./cassettes/` for saved recordings.

### 5. Replay

```bash
TIMETRACER_MODE=replay \
TIMETRACER_CASSETTE=./cassettes/GET__your-endpoint__abc123.json \
uvicorn main:app
```

Your app runs with all external calls mocked.

---

## Starlette

> **Note**: Starlette is the lightweight ASGI framework that FastAPI is built on. The integration is identical!

### 1. Install

```bash
pip install timetracer starlette httpx
```

### 2. Add Middleware

```python
# app.py
from starlette.applications import Starlette
from timetracer.integrations.starlette import TimeTracerMiddleware

app = Starlette(debug=True)
app.add_middleware(TimeTracerMiddleware)
```

Or use the one-liner:
```python
from timetracer.integrations.starlette import auto_setup
auto_setup(app, plugins=["httpx"])
```

### 3. Enable HTTP Client Plugin

```python
from timetracer.plugins import enable_httpx
enable_httpx()
```

### 4. Record

```bash
TIMETRACER_MODE=record uvicorn app:app --reload
```

Make some requests:
```bash
curl http://localhost:8000/your-endpoint
```

Check `./cassettes/` for saved recordings.

### 5. Replay

```bash
TIMETRACER_MODE=replay \
TIMETRACER_CASSETTE=./cassettes/GET__your-endpoint__abc123.json \
uvicorn app:app
```

Your app runs with all external calls mocked. See [full Starlette docs](starlette.md).

---

## Flask

### 1. Install

```bash
pip install timetracer[flask,requests]
```

### 2. Add Middleware

```python
# app.py
from flask import Flask
from timetracer.integrations.flask import TimeTracerMiddleware

app = Flask(__name__)
app.wsgi_app = TimeTracerMiddleware(app.wsgi_app)
```

### 3. Enable HTTP Client Plugin

```python
from timetracer.plugins import enable_requests
enable_requests()
```

### 4. Record

```bash
TIMETRACER_MODE=record flask run
```

Make requests, then check `./cassettes/`.

### 5. Replay

```bash
TIMETRACER_MODE=replay \
TIMETRACER_CASSETTE=./cassettes/your-cassette.json \
flask run
```

---

## Django

### 1. Install

```bash
pip install timetracer[django,requests]
```

### 2. Add Middleware

```python
# settings.py
MIDDLEWARE = [
    'timetracer.integrations.django.TimeTracerMiddleware',
    'django.middleware.common.CommonMiddleware',
    # ... other middleware
]
```

### 3. Enable HTTP Client Plugin

```python
# In your app's apps.py
from django.apps import AppConfig

class MyAppConfig(AppConfig):
    name = 'myapp'

    def ready(self):
        from timetracer.integrations.django import auto_setup
        auto_setup(plugins=['requests'])
```

### 4. Record

```bash
TIMETRACER_MODE=record python manage.py runserver
```

### 5. Replay

```bash
TIMETRACER_MODE=replay \
TIMETRACER_CASSETTE=./cassettes/your-cassette.json \
python manage.py runserver
```

---

## pytest

The pytest plugin auto-registers when you install Timetracer.

### 1. Install

```bash
pip install timetracer
```

### 2. Use Fixtures in Tests

```python
# test_my_api.py

def test_with_replay(timetracer_replay, client):
    """Test using a pre-recorded cassette."""
    with timetracer_replay("cassettes/my_test.json"):
        response = client.get("/api/users")
        assert response.status_code == 200


def test_record_new(timetracer_record, client):
    """Record a new cassette."""
    with timetracer_record("cassettes/new_test.json"):
        response = client.get("/api/users")
    # Cassette saved after test


def test_auto_mode(timetracer_auto, client):
    """Record if missing, replay if exists."""
    with timetracer_auto("cassettes/auto_test.json"):
        response = client.get("/api/users")
```

### 3. Run Tests

```bash
pytest test_my_api.py -v
```

### Available Fixtures

| Fixture | What It Does |
|---------|--------------|
| `timetracer_replay` | Load cassette and mock external calls |
| `timetracer_record` | Record new cassette during test |
| `timetracer_auto` | Record first time, replay after |
| `timetracer_cassette_dir` | Get path to cassettes directory |

---

## Common Configuration

Environment variables work with all frameworks:

| Variable | Default | Description |
|----------|---------|-------------|
| `TIMETRACER_MODE` | off | `record`, `replay`, or `off` |
| `TIMETRACER_DIR` | ./cassettes | Where cassettes are saved |
| `TIMETRACER_CASSETTE` | - | Path to cassette for replay |
| `TIMETRACER_SAMPLE_RATE` | 1.0 | Record only X% of requests |
| `TIMETRACER_ERRORS_ONLY` | false | Only record failed requests |

---

## Typical Workflow

1. **Develop locally** with `TIMETRACER_MODE=record`
2. **Bug happens** in production
3. **Download cassette** from S3/logs
4. **Replay locally** with exact same inputs
5. **Debug and fix** without touching production
6. **Commit cassette** to repo for regression testing

---

## Need Help?

- See `examples/` folder for complete working examples
- Check `docs/` for detailed documentation
- Open an issue on GitHub
