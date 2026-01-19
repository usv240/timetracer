# Django Example

Complete example of Timetracer with Django.

## Files

- `settings.py` - Django settings with Timetracer middleware
- `views.py` - Views that make external HTTP calls
- `urls.py` - URL routing
- `test_views.py` - Tests using pytest fixtures

## Quick Start

### 1. Install

```bash
pip install timetracer[django,requests]
```

### 2. Add Middleware (already done in settings.py)

```python
# settings.py
MIDDLEWARE = [
    'timetracer.integrations.django.TimeTracerMiddleware',
    # ... other middleware
]

# Optional configuration
TIMETRACER = {
    'MODE': 'record',
    'CASSETTE_DIR': './cassettes',
}
```

### 3. Enable Plugins (already done in views.py)

```python
# views.py
from timetracer.integrations.django import auto_setup
auto_setup(plugins=['requests'])
```

### 4. Run Server in Record Mode

```bash
cd examples/django_app
TIMETRACER_MODE=record python manage.py runserver
```

### 5. Make Requests

```bash
# Health check
curl http://localhost:8000/

# List users (local data, no external call)
curl http://localhost:8000/api/users/

# Fetch external API (this call gets recorded)
curl http://localhost:8000/api/fetch-external/
```

Cassettes are saved to `./cassettes/`.

### 6. Replay Later

```bash
TIMETRACER_MODE=replay \
TIMETRACER_CASSETTE=./cassettes/GET__api_fetch-external.json \
python manage.py runserver
```

The external API call is now mocked - no network needed.

## Run Tests

```bash
pytest test_views.py -v
```

## Key Concepts

1. **Middleware** captures all requests/responses
2. **Plugins** capture outbound HTTP calls (requests, httpx, aiohttp)
3. **Cassettes** store everything as JSON
4. **Replay** mocks external calls using recorded data
