# Django Integration

Timetracer supports Django 3.2 LTS and later, including async views in Django 4.1+.

## Installation

```bash
pip install timetracer[django]
```

## Quick Start

Add the middleware to your Django settings:

```python
# settings.py
MIDDLEWARE = [
    'timetracer.integrations.django.TimeTracerMiddleware',
    'django.middleware.security.SecurityMiddleware',
    # ... other middleware
]
```

Configure via environment variables:

```bash
export TIMETRACER_MODE=record
export TIMETRACER_DIR=./cassettes
```

Or configure in settings.py:

```python
# settings.py
TIMETRACER = {
    'MODE': 'record',
    'CASSETTE_DIR': './cassettes',
    'EXCLUDE_PATHS': ['/admin/', '/static/'],
}
```

## Configuration Options

| Setting | Environment Variable | Default | Description |
|---------|---------------------|---------|-------------|
| MODE | TIMETRACER_MODE | off | "record", "replay", or "off" |
| CASSETTE_DIR | TIMETRACER_DIR | ./cassettes | Where to save cassettes |
| CASSETTE_PATH | TIMETRACER_CASSETTE | None | Specific cassette for replay |
| SAMPLE_RATE | TIMETRACER_SAMPLE_RATE | 1.0 | Sampling rate (0.0-1.0) |
| ERRORS_ONLY | TIMETRACER_ERRORS_ONLY | false | Only record errors |
| EXCLUDE_PATHS | - | [] | Paths to exclude from tracing |
| MAX_BODY_KB | TIMETRACER_MAX_BODY_KB | 64 | Max body size to capture |

## Enable Plugins

For Django apps, call `auto_setup()` in your app config:

```python
# myapp/apps.py
from django.apps import AppConfig

class MyAppConfig(AppConfig):
    name = 'myapp'

    def ready(self):
        from timetracer.integrations.django import auto_setup
        auto_setup(plugins=['requests', 'redis'])
```

Or in settings.py:

```python
# settings.py
from timetracer.integrations.django import auto_setup
auto_setup(plugins=['requests', 'sqlalchemy'])
```

## Django REST Framework

Timetracer works with DRF out of the box. The middleware captures requests at the WSGI/ASGI level, so serializers and views work normally.

```python
# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
import requests

class UserView(APIView):
    def get(self, request, user_id):
        # This requests call will be captured
        resp = requests.get(f'https://api.example.com/users/{user_id}')
        return Response(resp.json())
```

## Async Views (Django 4.1+)

Async views are fully supported:

```python
# views.py
import aiohttp
from django.http import JsonResponse

async def async_view(request):
    async with aiohttp.ClientSession() as session:
        async with session.get('https://api.example.com/data') as resp:
            data = await resp.json()
    return JsonResponse(data)
```

Make sure to enable the aiohttp plugin:

```python
auto_setup(plugins=['aiohttp'])
```

## Recording

Run your Django server in record mode:

```bash
TIMETRACER_MODE=record python manage.py runserver
```

Make requests to your API - cassettes are saved automatically.

## Replaying

Run with a specific cassette:

```bash
TIMETRACER_MODE=replay \
TIMETRACER_CASSETTE=./cassettes/GET__api_users.json \
python manage.py runserver
```

All external calls are mocked using the recorded data.

## Production Usage

For production, use sampling to reduce overhead:

```python
# settings.py
TIMETRACER = {
    'MODE': 'record',
    'SAMPLE_RATE': 0.1,  # Record 10% of requests
    'ERRORS_ONLY': True,  # Or just record errors
}
```
