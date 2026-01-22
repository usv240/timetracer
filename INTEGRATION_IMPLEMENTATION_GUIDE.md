# Implementation Guide - Top Priority Integrations

Quick implementation guides for the highest-impact integrations.

---

## 1. PyMongo Integration (Week 1)

### Overview
Add synchronous MongoDB support to complement existing Motor (async) support.

### Implementation

**File:** `src/timetracer/plugins/pymongo_plugin.py`

```python
"""PyMongo (MongoDB sync) plugin for Timetracer."""

import functools
from typing import Any

from timetracer.context import get_session
from timetracer.plugins.base import Plugin
from timetracer.types import DependencyEvent, DependencySignature, EventResult

try:
    import pymongo
    from pymongo.collection import Collection
    PYMONGO_AVAILABLE = True
except ImportError:
    PYMONGO_AVAILABLE = False
    Collection = None


class PyMongoPlugin(Plugin):
    """Plugin for recording PyMongo operations."""

    name = "pymongo"
    
    def __init__(self):
        self._original_methods = {}
    
    def enable_recording(self) -> None:
        """Patch PyMongo collection methods."""
        if not PYMONGO_AVAILABLE:
            return
        
        # Patch Collection methods
        methods = [
            'find_one', 'insert_one', 'insert_many',
            'update_one', 'update_many', 'replace_one',
            'delete_one', 'delete_many', 'count_documents',
            'find', 'aggregate'
        ]
        
        for method_name in methods:
            original = getattr(Collection, method_name)
            self._original_methods[method_name] = original
            setattr(Collection, method_name, self._wrap_method(method_name, original))
    
    def enable_replay(self) -> None:
        """Mock PyMongo methods for replay."""
        # Similar to Motor plugin
        pass
    
    def _wrap_method(self, method_name: str, original_method):
        """Wrap a PyMongo method to record its execution."""
        
        @functools.wraps(original_method)
        def wrapper(self, *args, **kwargs):
            session = get_session()
            if not session or not session.is_recording:
                return original_method(self, *args, **kwargs)
            
            # Build signature
            signature = DependencySignature(
                lib="pymongo",
                method=method_name.upper(),
                url=f"{self.database.name}.{self.name}"
            )
            
            # Execute the operation
            import time
            start_time = time.perf_counter()
            
            try:
                result = original_method(self, *args, **kwargs)
                duration_ms = (time.perf_counter() - start_time) * 1000
                
                # Build event
                event = DependencyEvent(
                    type="db.query",
                    signature=signature,
                    request={"filter": args[0] if args else kwargs},
                    result=EventResult(
                        status=0,
                        body={"data": self._serialize_result(result)}
                    ),
                    duration_ms=duration_ms
                )
                
                session.add_dependency(event)
                return result
                
            except Exception as e:
                duration_ms = (time.perf_counter() - start_time) * 1000
                event = DependencyEvent(
                    type="db.query",
                    signature=signature,
                    request={"filter": args[0] if args else kwargs},
                    result=EventResult(
                        status=1,
                        body={"error": str(e)}
                    ),
                    duration_ms=duration_ms
                )
                session.add_dependency(event)
                raise
        
        return wrapper
    
    def _serialize_result(self, result: Any) -> Any:
        """Serialize MongoDB result to JSON-compatible format."""
        from bson import ObjectId
        from datetime import datetime
        
        if isinstance(result, dict):
            return {k: self._serialize_result(v) for k, v in result.items()}
        elif isinstance(result, list):
            return [self._serialize_result(item) for item in result]
        elif isinstance(result, ObjectId):
            return str(result)
        elif isinstance(result, datetime):
            return result.isoformat()
        else:
            return result


# Global plugin instance
_pymongo_plugin = PyMongoPlugin()


def enable_pymongo() -> None:
    """Enable PyMongo recording."""
    if not PYMONGO_AVAILABLE:
        raise ImportError("pymongo is not installed. Install with: pip install pymongo")
    
    _pymongo_plugin.enable()


def disable_pymongo() -> None:
    """Disable PyMongo recording."""
    _pymongo_plugin.disable()
```

### Integration Test

**File:** `tests/unit/test_pymongo_plugin.py`

```python
import pytest
from timetracer.plugins.pymongo_plugin import enable_pymongo, disable_pymongo

pymongo = pytest.importorskip("pymongo")


def test_enable_pymongo():
    """Test that enabling PyMongo plugin works."""
    enable_pymongo()
    disable_pymongo()


def test_pymongo_find_one_signature():
    """Test PyMongo find_one creates correct signature."""
    # Test implementation
    pass
```

### Documentation

**File:** `docs/pymongo.md`

```markdown
# PyMongo Integration

Record and replay MongoDB operations using PyMongo (synchronous driver).

## Installation

```bash
pip install timetracer[motor]  # Installs pymongo as well
```

## Usage

```python
from pymongo import MongoClient
from timetracer.plugins import enable_pymongo

# Enable PyMongo plugin
enable_pymongo()

# Use PyMongo normally
client = MongoClient('mongodb://localhost:27017')
db = client.mydb

# All operations are recorded
user = db.users.find_one({"email": "user@example.com"})
db.orders.insert_one({"user_id": user["_id"], "total": 99.99})
```

## Supported Operations

- `find_one` - Find single document
- `insert_one` / `insert_many` - Insert documents
- `update_one` / `update_many` - Update documents  
- `delete_one` / `delete_many` - Delete documents
- `count_documents` - Count matching documents
- `find` - Query cursor (recorded on creation)
- `aggregate` - Aggregation pipeline

## Cassette Format

```json
{
  "events": [
    {
      "type": "db.query",
      "signature": {
        "lib": "pymongo",
        "method": "FIND_ONE",
        "url": "mydb.users"
      },
      "request": {
        "filter": {"email": "user@example.com"}
      },
      "result": {
        "status": 0,
        "body": {
          "data": {"_id": "507f1f77bcf86cd799439011", "email": "user@example.com"}
        }
      }
    }
  ]
}
```
```

**Effort:** 1 week  
**Impact:** +300K users (complete MongoDB coverage)

---

## 2. Starlette Integration (Week 2)

### Overview
Add native Starlette middleware (FastAPI is built on Starlette).

### Implementation

**File:** `src/timetracer/integrations/starlette.py`

```python
"""Starlette integration for Timetracer."""

from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from timetracer.config import TraceConfig
from timetracer.context import RecordingSession
from timetracer.integrations.fastapi import TimeTracerMiddleware  # Reuse!


def auto_setup(
    app: Starlette,
    config: TraceConfig | None = None,
    plugins: list[str] | None = None,
) -> Starlette:
    """
    Auto-configure Timetracer for Starlette.
    
    Args:
        app: Starlette application
        config: Optional TraceConfig (defaults to from_env())
        plugins: List of plugins to enable (e.g., ['httpx', 'redis'])
    
    Returns:
        The configured Starlette app
    """
    if config is None:
        config = TraceConfig.from_env()
    
    # Add Timetracer middleware
    app.add_middleware(TimeTracerMiddleware, config=config)
    
    # Enable plugins
    if plugins:
        from timetracer.plugins import enable_plugin
        for plugin in plugins:
            enable_plugin(plugin)
    
    return app
```

### Example

**File:** `examples/starlette_app/app.py`

```python
"""Example Starlette app with Timetracer."""

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from timetracer.integrations.starlette import auto_setup


async def homepage(request):
    return JSONResponse({"message": "Hello, World!"})


async def users(request):
    user_id = request.path_params['user_id']
    # Simulate database call
    return JSONResponse({"id": user_id, "name": "Alice"})


routes = [
    Route('/', endpoint=homepage),
    Route('/users/{user_id}', endpoint=users),
]

app = auto_setup(Starlette(routes=routes))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

**Effort:** 1 week (reuses FastAPI middleware)  
**Impact:** +100K users (Starlette purists)

---

## 3. Celery Integration (Weeks 3-6)

### Overview
**The most requested feature.** Record Celery task execution with full dependency context.

### Architecture

```
User Request → Web App → Celery Task
                            ↓
                    [Start Recording]
                            ↓
                    DB Query (captured)
                            ↓
                    API Call (captured)  
                            ↓
                    Redis (captured)
                            ↓
                    [Save Cassette]
```

### Implementation

**File:** `src/timetracer/integrations/celery.py`

```python
"""Celery integration for Timetracer."""

from typing import Any
import functools

from timetracer.config import TraceConfig
from timetracer.context import RecordingSession, set_session
from timetracer.cassette.io import write_cassette

try:
    from celery import Celery, Task
    from celery.signals import (
        task_prerun,
        task_postrun,
        task_failure,
    )
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    Celery = None
    Task = None


def enable_celery(app: Celery, config: TraceConfig | None = None) -> None:
    """
    Enable Timetracer for Celery tasks.
    
    Args:
        app: Celery application
        config: Optional TraceConfig (defaults to from_env())
    
    Example:
        from celery import Celery
        from timetracer.integrations.celery import enable_celery
        
        app = Celery('myapp')
        enable_celery(app)
        
        @app.task
        def process_order(order_id):
            # All dependencies recorded
            order = db.orders.find(order_id)
            payment = stripe.charge(order.total)
            return payment.id
    """
    if not CELERY_AVAILABLE:
        raise ImportError("celery is not installed")
    
    if config is None:
        config = TraceConfig.from_env()
    
    # Store config on app
    app.conf.timetracer_config = config
    
    # Register signal handlers
    @task_prerun.connect
    def start_recording(sender=None, task_id=None, task=None, args=None, kwargs=None, **extra):
        """Start recording before task execution."""
        if config.mode.value != "record":
            return
        
        # Create session for this task
        session = RecordingSession(
            session_id=task_id,
            config=config,
            request_method="TASK",
            request_path=f"celery.{task.name}",
        )
        
        # Store task metadata
        session.metadata["task_name"] = task.name
        session.metadata["task_args"] = args
        session.metadata["task_kwargs"] = kwargs
        
        # Set as current session
        set_session(session)
    
    @task_postrun.connect
    def finish_recording(sender=None, task_id=None, task=None, retval=None, **extra):
        """Save recording after successful task completion."""
        session = get_session()
        if not session:
            return
        
        # Store result
        session.metadata["task_result"] = retval
        
        # Save cassette
        session.finalize()
        cassette_path = write_cassette(session, config)
        
        # Log
        print(f"Timetracer: Recorded task {task.name} → {cassette_path}")
        
        # Clear session
        set_session(None)
    
    @task_failure.connect
    def record_failure(sender=None, task_id=None, exception=None, traceback=None, **extra):
        """Save recording on task failure."""
        session = get_session()
        if not session:
            return
        
        # Store error details
        session.metadata["task_error"] = str(exception)
        session.metadata["task_traceback"] = str(traceback)
        
        # Save cassette
        session.finalize()
        cassette_path = write_cassette(session, config)
        
        print(f"Timetracer: Recorded failed task → {cassette_path}")
        
        # Clear session
        set_session(None)
```

### Example

**File:** `examples/celery_app/tasks.py`

```python
"""Example Celery tasks with Timetracer."""

from celery import Celery
from timetracer.integrations.celery import enable_celery
from timetracer.plugins import enable_httpx, enable_redis

# Create Celery app
app = Celery('myapp', broker='redis://localhost:6379/0')

# Enable Timetracer
enable_celery(app)
enable_httpx()  # Record HTTP calls
enable_redis()  # Record Redis operations

@app.task
def process_payment(order_id: int):
    """Process payment for an order."""
    import httpx
    import redis
    
    # All of these are captured:
    r = redis.Redis()
    order_data = r.get(f"order:{order_id}")
    
    # Make payment API call
    response = httpx.post(
        "https://api.stripe.com/v1/charges",
        data={"amount": 1999, "currency": "usd"}
    )
    
    # Update cache
    r.set(f"payment:{order_id}", response.json()["id"])
    
    return response.json()


@app.task
def send_email(user_id: int, subject: str):
    """Send email to user."""
    import httpx
    
    # Fetch user
    user = httpx.get(f"https://api.example.com/users/{user_id}").json()
    
    # Send email
    result = httpx.post(
        "https://api.sendgrid.com/v3/mail/send",
        json={
            "to": user["email"],
            "subject": subject
        }
    )
    
    return result.status_code == 200
```

### Replay Failed Tasks

```bash
# A Celery task failed in production
# You have the cassette: celery_process_payment_failed_abc123.json

# Replay locally to debug
TIMETRACER_MODE=replay \
  TIMETRACER_CASSETTE=./cassettes/celery_process_payment_failed_abc123.json \
  python -c "
from tasks import process_payment
result = process_payment(order_id=12345)
# Runs with exact same DB/API responses as production!
"
```

### Documentation

**File:** `docs/celery.md`

```markdown
# Celery Integration

Record and replay async task execution with full dependency context.

## Installation

```bash
pip install timetracer[celery]
```

## Usage

```python
from celery import Celery
from timetracer.integrations.celery import enable_celery

app = Celery('myapp')
enable_celery(app)

@app.task
def my_task(arg):
    # All DB queries, API calls, Redis ops recorded
    pass
```

## Debugging Failed Tasks

When a task fails in production:

1. Cassette is automatically saved
2. Download cassette to local machine
3. Replay task with exact production state
4. Fix bug, verify fix works

## Benefits

- Debug production failures locally
- No need to access production databases
- Reproduce exact conditions that caused failure
- Test task fixes without running tasks
```

**Effort:** 4 weeks  
**Impact:** +500K users (every Django/Flask production app)  
**Differentiator:** NO competitor has this!

---

## 4. asyncpg Integration (Weeks 7-9)

### Overview
PostgreSQL async driver - the standard for FastAPI apps.

### Key Features

```python
import asyncpg
from timetracer.plugins import enable_asyncpg

enable_asyncpg()

# Captures:
# - SQL queries with parameters
# - Query results  
# - Execution time
# - Transaction boundaries
# - Connection pool stats

conn = await asyncpg.connect('postgresql://...')
users = await conn.fetch('SELECT * FROM users WHERE age > $1', 18)
```

### Implementation

**File:** `src/timetracer/plugins/asyncpg_plugin.py`

```python
"""asyncpg (PostgreSQL async) plugin."""

# Similar structure to Motor plugin
# Wrap Connection methods: execute, fetch, fetchrow, executemany
# Record SQL, params, results, timing
# Support transactions
```

**Effort:** 3 weeks  
**Impact:** +200K users (PostgreSQL + async)

---

## 5. boto3/AWS Integration (Weeks 10-15)

### Overview
Record and replay AWS API calls - develop offline!

### Supported Services (Priority Order)

1. **S3** - Object storage
2. **DynamoDB** - NoSQL database
3. **SQS** - Message queue
4. **SNS** - Pub/sub messaging
5. **Lambda** - Function invocation

### Example

```python
import boto3
from timetracer.plugins import enable_boto3

enable_boto3()

# Recording: real AWS calls
s3 = boto3.client('s3')
s3.put_object(Bucket='mybucket', Key='data.json', Body=b'{"test": true}')

# Replay: works offline, no AWS credentials needed!
TIMETRACER_MODE=replay python app.py
```

**Effort:** 6 weeks (complex, many services)  
**Impact:** +1M users (every cloud app)  
**Value:** Eliminate dev/staging AWS costs

---

## Implementation Priority

| Week | Integration | Output |
|------|-------------|--------|
| 1 | PyMongo | MongoDB sync support |
| 2 | Starlette | Framework support |
| 3-6 | Celery | Task queue (HUGE) |
| 7-9 | asyncpg | PostgreSQL async |
| 10-12 | psycopg3 | PostgreSQL sync |
| 13-18 | boto3 | AWS services |

**6-month result:** 6 major integrations, 4x user growth

---

## Next Steps

1. Start with **PyMongo** (easiest, 1 week)
2. Add **Starlette** (leverages existing code)
3. Begin **Celery** design (most impactful)

Each integration should include:
- ✅ Plugin implementation
- ✅ Unit tests
- ✅ Integration tests
- ✅ Example project
- ✅ Documentation
- ✅ Announcement blog post
