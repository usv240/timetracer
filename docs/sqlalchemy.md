# SQLAlchemy Plugin

Capture and replay SQLAlchemy database queries.

## Installation

```bash
pip install timetracer[sqlalchemy]
```

## Usage

```python
from fastapi import FastAPI
from sqlalchemy import create_engine
from timetracer.config import TraceConfig
from timetracer.integrations.fastapi import timetracerMiddleware
from timetracer.plugins import enable_sqlalchemy

# Create engine
engine = create_engine("postgresql://user:pass@localhost/db")

# Enable SQLAlchemy capture
enable_sqlalchemy(engine)

# Or enable globally for all engines
enable_sqlalchemy()

app = FastAPI()
config = TraceConfig.from_env()
app.add_middleware(timetracerMiddleware, config=config)
```

## What Gets Captured

For each database query, timetracer records:

| Field | Description |
|-------|-------------|
| `event_type` | `db.query` |
| `method` | SQL operation (SELECT, INSERT, UPDATE, DELETE) |
| `url` | Table name |
| `body_hash` | Hash of query parameters |
| `duration_ms` | Query execution time |
| `status` | Row count affected |

## Example Cassette Event

```json
{
  "eid": 2,
  "type": "db.query",
  "start_offset_ms": 45,
  "duration_ms": 12,
  "signature": {
    "lib": "sqlalchemy",
    "method": "SELECT",
    "url": "users",
    "body_hash": "sha256:abc123..."
  },
  "result": {
    "status": 5,
    "headers": {"rowcount": "5"}
  }
}
```

## Hybrid Replay

Mock HTTP but keep database live:

```python
config = TraceConfig(
    mode="replay",
    mock_plugins=["http"],  # Mock HTTP only
    live_plugins=["db"],    # Keep DB live
)
```

## Limitations

- **v2.0**: Query result mocking is not yet supported (only timing captured)
- Complex query result sets are not stored in cassettes
- For full DB mocking, consider using a test database with fixtures
