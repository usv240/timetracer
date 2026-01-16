# Timetrace Plugin System

Learn how to use and create plugins for Timetrace.

## Built-in Plugins

### httpx Plugin

Captures and replays httpx HTTP client calls.

```python
from timetrace.plugins.httpx_plugin import enable_httpx, disable_httpx

# Enable capturing
enable_httpx()

# Your code using httpx will now be captured
async with httpx.AsyncClient() as client:
    response = await client.get("https://api.example.com/data")

# Disable when done (optional)
disable_httpx()
```

### requests Plugin

Captures and replays requests library calls.

```python
from timetrace.plugins.requests_plugin import enable_requests, disable_requests

enable_requests()

# Your code using requests will now be captured
response = requests.get("https://api.example.com/data")

disable_requests()
```

### SQLAlchemy Plugin

Captures database queries (SELECT, INSERT, UPDATE, DELETE).

```python
from timetrace.plugins import enable_sqlalchemy
from sqlalchemy import create_engine

engine = create_engine("postgresql://...")
enable_sqlalchemy(engine)  # Or enable_sqlalchemy() for all engines

# Your database queries will now be captured
```

See [SQLAlchemy docs](sqlalchemy.md) for details.

### Redis Plugin

Captures Redis commands.

```python
from timetrace.plugins import enable_redis

enable_redis()

# Your Redis commands will now be captured
redis_client.get("user:123")
redis_client.set("cache:key", "value")
```

## Hybrid Replay Mode

One of Timetrace's most powerful features is **hybrid replay**, which allows you to:
- Mock some dependencies while keeping others live
- Test against real databases while mocking external APIs
- Gradually add mocking to complex systems

### Configuration

```python
from timetrace.config import TraceConfig

# Option 1: Specify what to mock (everything else stays live)
config = TraceConfig(
    mode="replay",
    cassette_path="./cassettes/checkout.json",
    mock_plugins=["http"],  # Only mock HTTP calls
)

# Option 2: Specify what to keep live (everything else is mocked)
config = TraceConfig(
    mode="replay",
    cassette_path="./cassettes/checkout.json",
    live_plugins=["db", "redis"],  # Keep DB and Redis live
)
```

### Environment Variables

```bash
# Mock only HTTP, keep everything else live
TIMETRACER_MOCK_PLUGINS=http

# Keep DB and Redis live, mock everything else
TIMETRACER_LIVE_PLUGINS=db,redis
```

### Use Cases

**Testing external API integration:**
```python
# Mock Stripe API but use real database
config = TraceConfig(
    mode="replay",
    mock_plugins=["http"],  # Mock external HTTP calls
)
```

**Performance testing with real dependencies:**
```python
# Keep all dependencies live, just trace for analysis
config = TraceConfig(
    mode="record",
    live_plugins=["http", "db"],  # Everything stays live
)
```

## Plugin Interface

### Creating a Custom Plugin

Plugins intercept dependency calls during recording and replay.

```python
from timetrace.context import get_current_session, has_active_session
from timetrace.types import DependencyEvent, EventSignature, EventResult
from timetrace.constants import EventType

def enable_my_plugin():
    """Enable your custom plugin."""
    # 1. Store original function
    global _original_func
    _original_func = some_library.function
    
    # 2. Replace with instrumented version
    some_library.function = _instrumented_function

def _instrumented_function(*args, **kwargs):
    """Instrumented version of the original function."""
    # If no active session, use original
    if not has_active_session():
        return _original_func(*args, **kwargs)
    
    session = get_current_session()
    
    if session.is_recording:
        return _record_call(*args, **kwargs)
    elif session.is_replaying:
        # Check hybrid replay
        from timetrace.session import ReplaySession
        if isinstance(session, ReplaySession):
            if not session.should_mock_plugin("my_plugin"):
                return _original_func(*args, **kwargs)
        return _replay_call(*args, **kwargs)
    else:
        return _original_func(*args, **kwargs)
```

### Key Components

1. **EventSignature**: Identifies a call for matching
   - `lib`: Plugin name
   - `method`: Operation type
   - `url`: Target (for HTTP)
   - `body_hash`: Hash of request body

2. **EventResult**: Recorded response data
   - `status`: HTTP status or success indicator
   - `body`: Captured response body
   - `error`: Error information if failed

3. **DependencyEvent**: Complete recording
   - `eid`: Event ID
   - `event_type`: Type of event
   - `start_offset_ms`: When it started
   - `duration_ms`: How long it took
   - `signature`: Call signature
   - `result`: Call result

## Plugin Best Practices

1. **Always check for active session** before instrumenting
2. **Support hybrid replay** by checking `should_mock_plugin()`
3. **Store minimal data** - hash bodies instead of storing full content
4. **Handle errors gracefully** - record error info for replay
5. **Provide enable/disable functions** for clean teardown
