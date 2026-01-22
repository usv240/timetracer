# Motor/MongoDB Example

This example demonstrates using Timetracer with Motor (async MongoDB driver).

## Prerequisites

```bash
pip install motor pymongo
```

You'll also need a MongoDB instance running. Options:
- Local: `mongod` or Docker: `docker run -p 27017:27017 mongo`
- Cloud: MongoDB Atlas (free tier available)

## Features

The Motor plugin captures these MongoDB operations:
- `find_one`
- `insert_one` / `insert_many`
- `update_one` / `update_many`
- `delete_one` / `delete_many`
- `count_documents`
- `aggregate` (cursor creation)
- `find` (cursor creation)

## Quick Start

### 1. Enable the Motor Plugin

```python
from timetracer.plugins import enable_motor

enable_motor()  # Enable globally for all Motor clients
```

### 2. Add Timetracer Middleware

```python
from fastapi import FastAPI
from timetracer.integrations.fastapi import auto_setup

app = auto_setup(FastAPI())
```

### 3. Use Motor Normally

```python
from motor.motor_asyncio import AsyncIOMotorClient

client = AsyncIOMotorClient("mongodb://localhost:27017")
db = client.mydb

# These operations are automatically captured
await db.users.insert_one({"name": "Alice", "age": 30})
user = await db.users.find_one({"name": "Alice"})
```

## Running the Example

```bash
# Start MongoDB (if not running)
docker run -d -p 27017:27017 --name mongo mongo

# Run the example app in record mode
TIMETRACER_MODE=record python app.py

# Check the generated cassettes
ls cassettes/
```

## Cassette Content

The cassette will include MongoDB operations like:

```json
{
  "events": [
    {
      "type": "db.query",
      "signature": {
        "lib": "motor",
        "method": "FIND_ONE",
        "url": "mydb.users"
      },
      "result": {
        "status": 0,
        "body": {
          "data": {"_id": "...", "name": "Alice", "age": 30}
        }
      },
      "duration_ms": 2.5
    }
  ]
}
```

## Configuration

Enable via environment:

```bash
# Enable motor plugin during auto_setup
TIMETRACER_CAPTURE=http,motor
```

Or via code:

```python
from timetracer.plugins import enable_motor, enable_httpx

enable_motor()   # Capture MongoDB
enable_httpx()   # Capture HTTP too
```

## Redaction

Sensitive MongoDB fields are automatically redacted based on field names:
- `password`, `token`, `api_key`, etc.
- Email addresses, phone numbers, SSNs

## pytest Integration

```python
def test_user_creation(timetracer_replay):
    with timetracer_replay("create_user.json", plugins=["motor"]):
        # MongoDB calls are mocked from cassette
        result = await db.users.insert_one({"name": "Test"})
        assert result.acknowledged
```

## Notes

- **Cursors**: `find()` and `aggregate()` return cursors. The cursor creation is recorded, but iteration is not mocked during replay.
- **ObjectId**: ObjectIds are serialized to strings in cassettes.
- **Replay**: Currently, the motor plugin supports recording. Full replay mocking for MongoDB is a future feature.
