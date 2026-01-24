# Motor (MongoDB) Plugin

Timetracer captures async MongoDB operations via the Motor driver, enabling time-travel debugging for MongoDB-based applications.

## Installation

```bash
pip install timetracer[motor]
# or
pip install timetracer motor
```

## Quick Start

```python
from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient
from timetracer.integrations.fastapi import auto_setup
from timetracer.plugins import enable_motor

# Enable Motor plugin
enable_motor()

# Setup FastAPI with Timetracer
app = auto_setup(FastAPI())

# Use Motor normally
client = AsyncIOMotorClient("mongodb://localhost:27017")
db = client.myapp

@app.get("/users/{user_id}")
async def get_user(user_id: str):
    # This operation is automatically captured!
    user = await db.users.find_one({"_id": user_id})
    return user
```

## Supported Operations

| Operation | Captured | Notes |
|-----------|----------|-------|
| `find_one` | Yes | Full capture with timing |
| `insert_one` | Yes | Captures inserted_id |
| `insert_many` | Yes | Captures count |
| `update_one` | Yes | Captures matched/modified counts |
| `update_many` | Yes | Captures matched/modified counts |
| `delete_one` | Yes | Captures deleted count |
| `delete_many` | Yes | Captures deleted count |
| `count_documents` | Yes | Captures count result |
| `aggregate` | Partial | Cursor creation captured |
| `find` | Partial | Cursor creation captured |

**Note:** For `find()` and `aggregate()`, the cursor creation is captured, but individual document iteration is not. This is because cursors are lazy and may be iterated outside the plugin's scope.

## How It Works

The Motor plugin patches `AsyncIOMotorCollection` methods to:

1. **Record mode**: Capture operation details, timing, and results
2. **Replay mode**: (Future) Return mocked results from cassettes

```
┌──────────────┐     ┌─────────────────┐     ┌──────────────┐
│   Your App   │ ──► │  Motor Plugin   │ ──► │   MongoDB    │
│              │     │  (intercepts)   │     │   Server     │
└──────────────┘     └─────────────────┘     └──────────────┘
                            │
                            ▼
                     ┌──────────────┐
                     │   Cassette   │
                     │   (events)   │
                     └──────────────┘
```

## Cassette Event Format

MongoDB operations are recorded as `db.query` events:

```json
{
  "events": [
    {
      "eid": 1,
      "type": "db.query",
      "start_offset_ms": 15.2,
      "duration_ms": 3.5,
      "signature": {
        "lib": "motor",
        "method": "FIND_ONE",
        "url": "myapp.users",
        "query": {
          "filter_keys": ["email", "active"]
        },
        "body_hash": "a1b2c3..."
      },
      "result": {
        "status": 0,
        "body": {
          "data": {
            "_id": "507f1f77bcf86cd799439011",
            "email": "user@example.com",
            "active": true
          }
        }
      }
    }
  ]
}
```

## Configuration

### Enable Globally

```python
from timetracer.plugins import enable_motor

enable_motor()  # Patches all Motor collections
```

### Enable/Disable

```python
from timetracer.plugins import enable_motor, disable_motor

# Enable at app startup
enable_motor()

# Disable when done (restores original behavior)
disable_motor()
```

### With Other Plugins

```python
from timetracer.plugins import enable_motor, enable_httpx, enable_redis

# Enable multiple plugins
enable_motor()   # MongoDB
enable_httpx()   # HTTP calls
enable_redis()   # Redis commands
```

## pytest Integration

Use Motor in tests:

```python
import pytest
from motor.motor_asyncio import AsyncIOMotorClient

@pytest.fixture
async def db():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    yield client.test_db
    client.close()

def test_user_lookup(timetracer_replay, db):
    with timetracer_replay("find_user.json", plugins=["motor"]):
        user = await db.users.find_one({"email": "test@example.com"})
        assert user is not None
```

## Security & Redaction

MongoDB documents are automatically redacted:

### Sensitive Fields Masked
- `password`, `token`, `api_key`
- `ssn`, `credit_card`
- `email`, `phone` (PII detection)

### ObjectId Handling
ObjectIds are serialized to strings:

```python
# Original
{"_id": ObjectId("507f1f77bcf86cd799439011")}

# In cassette
{"_id": "507f1f77bcf86cd799439011"}
```

### DateTime Handling
Datetimes are serialized to ISO format:

```python
# Original
{"created_at": datetime(2026, 1, 22, 12, 0, 0)}

# In cassette
{"created_at": "2026-01-22T12:00:00"}
```

## Testing Approach

Since MongoDB may not be available in all test environments, we use a **simulation approach**:

### Unit Tests (No MongoDB Required)
We test the plugin's internal functions:
- Signature creation
- Result building
- Serialization

```python
# tests/unit/test_motor_plugin.py
def test_make_signature():
    sig = _make_signature(
        operation="find_one",
        db_name="testdb",
        collection_name="users",
        filter_doc={"email": "test@example.com"},
        update_doc=None,
    )
    assert sig.lib == "motor"
    assert sig.method == "FIND_ONE"
```

### Integration Tests (Mocked Motor)
We mock the Motor library to simulate MongoDB behavior:

```python
# tests/integration/test_motor_integration.py
@pytest.fixture
def mock_collection():
    """Create a mock Motor collection."""
    collection = AsyncMock()
    collection.name = "users"
    collection.database.name = "testdb"
    collection.find_one.return_value = {"_id": "123", "name": "Test"}
    return collection
```

### End-to-End Tests (Real MongoDB)
For full E2E testing, use Docker:

```bash
# Start MongoDB
docker run -d -p 27017:27017 --name mongo-test mongo

# Run E2E tests
pytest tests/e2e/test_motor_e2e.py -v

# Cleanup
docker stop mongo-test && docker rm mongo-test
```

## Limitations

1. **Cursor Iteration**: The plugin captures cursor creation, but individual document iteration is not mocked during replay.

2. **Transactions**: Multi-document transactions are not specially handled yet.

3. **GridFS**: GridFS operations are not captured.

4. **Replay Mocking**: Currently, the plugin focuses on recording. Full replay mocking (returning cassette data instead of hitting MongoDB) is planned for a future release.

## Troubleshooting

### Plugin Not Capturing

Ensure the plugin is enabled **before** creating Motor clients:

```python
# Correct order
enable_motor()
client = AsyncIOMotorClient(...)

# Wrong order - plugin won't capture
client = AsyncIOMotorClient(...)
enable_motor()  # Too late!
```

### Import Error

```bash
# Install Motor
pip install motor

# Or with Timetracer
pip install timetracer[motor]
```

### ObjectId Serialization

If you see `ObjectId not JSON serializable`, the plugin handles this automatically. Ensure you're using Timetracer's cassette writing:

```python
from timetracer.cassette.io import write_cassette
# Not: json.dump(cassette)
```

## Example Project

See `examples/motor_mongodb/` for a complete working example:

```bash
cd examples/motor_mongodb
python app.py
```
