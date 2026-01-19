# Implementation Plan: Django + pytest Integration

## Overview

Adding two major integrations for v1.4.0:
1. Django middleware (sync + async support)
2. pytest plugin with fixtures

---

## Part 1: Django Integration

### Requirements
- Django 3.2+ (LTS)
- Django 4.0+ (async views)
- Django REST Framework compatibility
- Same configuration via environment variables

### Architecture

```
src/timetracer/integrations/django.py
```

### Django Middleware Pattern

Django middleware is different from WSGI/ASGI:

```python
# settings.py
MIDDLEWARE = [
    'timetracer.integrations.django.TimeTracerMiddleware',
    # ... other middleware
]

# Or manual setup
TIMETRACER = {
    'MODE': 'record',
    'CASSETTE_DIR': './cassettes',
}
```

### Key Differences from Flask/FastAPI

| Aspect | Flask | FastAPI | Django |
|--------|-------|---------|--------|
| Protocol | WSGI | ASGI | Both |
| Async | No | Yes | Optional (4.0+) |
| Config | env vars | env vars | settings.py + env vars |
| Request | environ dict | scope dict | HttpRequest object |
| Response | generator | ASGI messages | HttpResponse object |

### Implementation Steps

1. Create `django.py` with middleware class
2. Support both sync and async views
3. Read config from Django settings OR environment
4. Capture HttpRequest/HttpResponse properly
5. Handle DRF serializers if present
6. Add to `__init__.py` exports
7. Update pyproject.toml with django optional dep
8. Write tests
9. Create example project

### Django Middleware Structure

```python
class TimeTracerMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.config = self._load_config()
    
    def __call__(self, request):
        # Sync path
        if not self.config.is_enabled:
            return self.get_response(request)
        
        if self.config.is_record_mode:
            return self._handle_record_sync(request)
        elif self.config.is_replay_mode:
            return self._handle_replay_sync(request)
        return self.get_response(request)
    
    async def __acall__(self, request):
        # Async path (Django 4.1+)
        ...
```

---

## Part 2: pytest Plugin

### Requirements
- pytest 7.0+
- pytest-asyncio compatibility
- Works with any framework (not just FastAPI)

### Architecture

```
src/timetracer/pytest_plugin.py
# or
pytest-timetracer/ (separate package)
```

### Usage Patterns

```python
# Pattern 1: Marker-based
@pytest.mark.cassette("checkout.json")
def test_checkout(client):
    response = client.post("/checkout")
    assert response.status_code == 200

# Pattern 2: Fixture-based
def test_checkout(timetracer_replay, client):
    with timetracer_replay("checkout.json"):
        response = client.post("/checkout")

# Pattern 3: Auto-record
@pytest.mark.cassette("checkout.json", record="new_episodes")
def test_checkout(client):
    # Records if cassette doesn't exist, replays if it does
    response = client.post("/checkout")
```

### Implementation Steps

1. Create pytest plugin with entry point
2. Implement `cassette` marker
3. Implement `timetracer_replay` fixture
4. Implement `timetracer_record` fixture
5. Add cassette directory configuration
6. Support auto-record mode
7. Add to pyproject.toml entry points
8. Write tests for the plugin itself
9. Documentation

### pytest Plugin Structure

```python
# conftest.py (auto-loaded by pytest)
import pytest
from timetracer.config import TraceConfig
from timetracer.cassette import read_cassette
from timetracer.context import set_session, reset_session
from timetracer.session import ReplaySession

def pytest_configure(config):
    config.addinivalue_line(
        "markers", "cassette(path): replay from cassette file"
    )

@pytest.fixture
def timetracer_replay():
    """Context manager for replay mode in tests."""
    ...

@pytest.fixture
def timetracer_record(tmp_path):
    """Context manager for record mode in tests."""
    ...
```

---

## File Structure After Implementation

```
src/timetracer/
├── integrations/
│   ├── __init__.py      # Updated exports
│   ├── fastapi.py
│   ├── flask.py
│   └── django.py        # NEW
├── pytest_plugin.py     # NEW
└── ...

tests/
├── unit/
│   └── test_django.py   # NEW
├── integration/
│   └── test_pytest_plugin.py  # NEW
└── ...

examples/
├── django_app/          # NEW
│   ├── manage.py
│   ├── mysite/
│   └── test_app.py
└── ...

docs/
├── django.md            # NEW
└── pytest.md            # NEW
```

---

## Order of Implementation

### Phase 1: Django (2-3 days)
1. [ ] Create django.py middleware
2. [ ] Support sync views
3. [ ] Support async views (Django 4.1+)
4. [ ] Settings.py config loading
5. [ ] DRF compatibility testing
6. [ ] Unit tests
7. [ ] Example project
8. [ ] Documentation

### Phase 2: pytest (1-2 days)
1. [ ] Create pytest_plugin.py
2. [ ] Implement cassette marker
3. [ ] Implement replay fixture
4. [ ] Implement record fixture
5. [ ] Entry point in pyproject.toml
6. [ ] Tests
7. [ ] Documentation

### Phase 3: Release
1. [ ] Update version to 1.4.0
2. [ ] Update RELEASE_NOTES.md
3. [ ] Update README.md
4. [ ] Commit and tag
5. [ ] GitHub release

---

## Risk Areas

1. **Django async compatibility** - Need to test with Django 4.1+ async views
2. **DRF serialization** - May need special handling for DRF responses
3. **pytest fixture scope** - Need to handle function/class/module scopes
4. **pytest-asyncio** - Ensure async tests work correctly

---

## Questions to Resolve

1. Should pytest plugin be a separate package (`pytest-timetracer`) or built-in?
   - Recommendation: Built-in first, extract later if popular

2. Should Django config come from settings.py or just env vars?
   - Recommendation: Both - settings.py overrides env vars

3. What Django versions to support?
   - Recommendation: 3.2 LTS, 4.0, 4.1, 4.2 LTS, 5.0
