# Starlette Integration

Timetracer provides full support for Starlette applications through ASGI middleware integration.

> **Note**: Starlette is the lightweight ASGI framework that FastAPI is built on. Since they share the same ASGI interface, Timetracer's integration works identically for both frameworks.

## Installation

```bash
pip install timetracer[starlette]
```

Or install with specific HTTP client:
```bash
pip install timetracer starlette httpx
```

## Quick Start

### Option 1: Auto Setup (Recommended)

The simplest way to integrate Timetracer:

```python
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.responses import JSONResponse
from timetracer.integrations.starlette import auto_setup
import httpx

async def homepage(request):
    async with httpx.AsyncClient() as client:
        response = await client.get("https://api.github.com/users/octocat")
        data = response.json()
    return JSONResponse({"user": data["login"]})

app = Starlette(debug=True, routes=[
    Route("/", homepage),
])

# Configure in one line
auto_setup(app, plugins=["httpx"])
```

### Option 2: Manual Setup

For more granular control:

```python
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.responses import JSONResponse
from timetracer.integrations.starlette import TimeTracerMiddleware
from timetracer.config import TraceConfig
from timetracer.plugins import enable_httpx
import httpx

async def homepage(request):
    async with httpx.AsyncClient() as client:
        response = await client.get("https://api.github.com/users/octocat")
        data = response.json()
    return JSONResponse({"user": data["login"]})

app = Starlette(debug=True, routes=[
    Route("/", homepage),
])

# Configure Timetracer
config = TraceConfig(
    mode="record",
    cassette_dir="./cassettes",
)

# Add middleware
app.add_middleware(TimeTracerMiddleware, config=config)

# Enable httpx plugin
enable_httpx()
```

## Usage

### Recording Requests

Start your application in record mode:

```bash
TIMETRACER_MODE=record uvicorn app:app --reload
```

Make requests to your application:
```bash
curl http://localhost:8000/
```

You'll see output similar to:
```
timetracer [OK] recorded GET /  id=a7f2  status=200  total=145ms  deps=http.client:1
  cassette: cassettes/2026-01-22/GET____a7f2.json
```

### Replaying Requests

Replay a recorded cassette:

```bash
TIMETRACER_MODE=replay \
TIMETRACER_CASSETTE=./cassettes/2026-01-22/GET____a7f2.json \
uvicorn app:app
```

All external HTTP calls will be mocked using the recorded responses.

## Configuration

### Environment Variables

Configure Timetracer using environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `TIMETRACER_MODE` | `off` | Operation mode: `record`, `replay`, or `off` |
| `TIMETRACER_DIR` | `./cassettes` | Directory for cassette storage |
| `TIMETRACER_CASSETTE` | - | Path to cassette for replay mode |
| `TIMETRACER_SAMPLE_RATE` | `1.0` | Sample rate (0.0-1.0) |
| `TIMETRACER_ERRORS_ONLY` | `false` | Only record failed requests |

### Programmatic Configuration

```python
from timetracer.config import TraceConfig
from timetracer.integrations.starlette import auto_setup

config = TraceConfig(
    mode="record",
    cassette_dir="./my-cassettes",
    sample_rate=0.5,  # Record 50% of requests
    errors_only=False,
    exclude_paths=["/health", "/metrics"],
)

auto_setup(app, config=config)
```

## Supported Plugins

All Timetracer plugins work with Starlette:

### HTTP Clients
- **httpx** - Async HTTP calls (recommended for Starlette)
- **requests** - Synchronous HTTP calls
- **aiohttp** - Alternative async HTTP client

### Databases
- **SQLAlchemy** - SQL database ORM
- **Motor** - Async MongoDB driver
- **PyMongo** - Synchronous MongoDB driver

### Caching
- **Redis** - Redis client (sync/async)

### Enable Multiple Plugins

```python
auto_setup(app, plugins=["httpx", "sqlalchemy", "redis"])
```

Or enable manually:
```python
from timetracer.plugins import enable_httpx, enable_sqlalchemy, enable_redis

enable_httpx()
enable_sqlalchemy()
enable_redis()
```

## Advanced Features

### Excluded Paths

Prevent tracing of health check endpoints:

```python
config = TraceConfig(
    mode="record",
    exclude_paths=["/health", "/metrics", "/ping"],
)
```

### Error-Only Recording

Record only failed requests:

```bash
TIMETRACER_MODE=record \
TIMETRACER_ERRORS_ONLY=true \
uvicorn app:app
```

### Sampling

Record a percentage of requests (useful for production):

```bash
TIMETRACER_MODE=record \
TIMETRACER_SAMPLE_RATE=0.1 \
uvicorn app:app
```

## Example: Complete API

Complete example with database and HTTP calls:

```python
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.responses import JSONResponse
from timetracer.integrations.starlette import auto_setup
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import httpx

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String)
    github_url = Column(String)

engine = create_engine("sqlite:///./test.db")
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

async def get_user(request):
    user_id = request.path_params["user_id"]
    
    # Database query (traced)
    session = Session()
    user = session.query(User).filter_by(id=user_id).first()
    session.close()
    
    if not user:
        return JSONResponse({"error": "not found"}, status_code=404)
    
    # HTTP call (traced)
    async with httpx.AsyncClient() as client:
        response = await client.get(user.github_url)
        github_data = response.json()
    
    return JSONResponse({
        "user": user.username,
        "github": github_data,
    })

app = Starlette(debug=True, routes=[
    Route("/users/{user_id:int}", get_user),
])

# Setup with multiple plugins
auto_setup(app, plugins=["httpx", "sqlalchemy"])
```

Run the application:
```bash
TIMETRACER_MODE=record uvicorn app:app --reload
curl http://localhost:8000/users/1
```

The cassette will capture both the database query and the HTTP call.

## Comparison with FastAPI

Since Starlette is FastAPI's foundation, the integration is identical:

| Feature | Starlette | FastAPI |
|---------|-----------|---------|
| Middleware | Same | Same |
| ASGI Support | Yes | Yes |
| Async/Await | Yes | Yes |
| Plugins | All | All |
| Performance | Identical | Identical |

**Key Difference**: FastAPI adds automatic API documentation, request validation, and dependency injection on top of Starlette.

## Benefits of Starlette with Timetracer

1. **Lightweight**: Starlette has minimal overhead compared to full frameworks
2. **Performance**: Direct ASGI access with efficient request handling
3. **Debugging**: Full request replay with all dependencies mocked
4. **Testing**: Record production scenarios and replay in tests
5. **Time Travel**: Debug production issues in local environment

## Integration with Testing

Use Timetracer's pytest plugin with Starlette:

```python
# test_app.py
from starlette.testclient import TestClient
from app import app

client = TestClient(app)

def test_with_replay(timetracer_replay):
    """Test using a pre-recorded cassette."""
    with timetracer_replay("cassettes/test_user.json"):
        response = client.get("/users/1")
        assert response.status_code == 200
        assert "github" in response.json()
```

## Troubleshooting

### Middleware Not Working

Ensure middleware is added correctly:

```python
# Correct
app = Starlette(routes=[...])
app.add_middleware(TimeTracerMiddleware)

# Incorrect - middleware added after routes are defined
app.add_middleware(TimeTracerMiddleware)
app.add_route("/", homepage)
```

### httpx Calls Not Traced

Verify the plugin is enabled:

```python
from timetracer.plugins import enable_httpx
enable_httpx()
```

### Cassettes Not Saving

Check that mode is set to record:

```bash
echo $TIMETRACER_MODE  # Should output "record"
```

## Related Documentation

- [Configuration Guide](configuration.md)
- [Plugins](plugins.md)
- [Dashboard](dashboard.md)
- [FastAPI Integration](integrations.md#fastapi)

## Additional Resources

- See `examples/starlette_example/` for a working example
- Open an issue on [GitHub](https://github.com/usv240/timetracer)
- Review the [full documentation](https://github.com/usv240/timetracer#readme)
