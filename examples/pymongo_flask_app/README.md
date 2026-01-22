# Flask + PyMongo + Timetracer Example

Demonstrates Timetracer integration with Flask and PyMongo (synchronous MongoDB).

## Prerequisites

```bash
pip install timetracer[flask] pymongo
```

You'll also need MongoDB running:
```bash
# Using Docker
docker run -d -p 27017:27017 --name mongo mongo

# Or install MongoDB locally
```

## Quick Start

### 1. Seed Test Data

```bash
python app.py
# In another terminal:
curl http://localhost:5000/seed
```

### 2. Record Mode

```bash
TIMETRACER_MODE=record python app.py
curl http://localhost:5000/users
```

This creates a cassette in `./cassettes/` containing:
- HTTP request details
- **MongoDB queries** (PyMongo operations)
- Response data

### 3. Replay Mode

```bash
# Stop MongoDB
docker stop mongo

# Replay from cassette - works WITHOUT MongoDB!
TIMETRACER_MODE=replay \
  TIMETRACER_CASSETTE=./cassettes/2026-01-22/GET__users__abc123.json \
  python app.py

curl http://localhost:5000/users
# Returns same data from cassette, no database needed!
```

## How It Works

```python
from flask import Flask
from pymongo import MongoClient
from timetracer.integrations.flask import auto_setup
from timetracer.plugins import enable_pymongo

# Enable Timetracer
app = auto_setup(Flask(__name__))
enable_pymongo()  # ← Captures all MongoDB operations

# Use PyMongo normally
client = MongoClient('mongodb://localhost:27017')
db = client.demo_db

@app.route('/users')
def list_users():
    # This query is automatically captured!
    users = list(db.users.find({}))
    return jsonify({"users": users})
```

## Captured Operations

The cassette will include:

```json
{
  "events": [
    {
      "type": "db.query",
      "signature": {
        "lib": "pymongo",
        "method": "FIND",
        "url": "demo_db.users"
      },
      "result": {
        "data": [
          {"_id": "...", "name": "Alice", "email": "alice@example.com"}
        ]
      },
      "duration_ms": 2.5
    }
  ]
}
```

## Use Cases

### 1. Debug Production Issues

```bash
# Production cassette recorded automatically
# Download it and replay locally

TIMETRACER_MODE=replay \
  TIMETRACER_CASSETTE=./production_error.json \
  python app.py

# Debug with exact same MongoDB state!
```

### 2. Offline Development

```bash
# Record once with MongoDB
TIMETRACER_MODE=record python app.py

# Develop offline indefinitely
TIMETRACER_MODE=replay python app.py
# No MongoDB needed!
```

### 3. Testing

```bash
# Create test cassettes from real scenarios
# Use in tests without mock setup

pytest  # Uses cassettes automatically via pytest plugin
```

## Endpoints

- `GET /` - Home page with endpoint list
- `GET /seed` - Seed test data (creates 3 users)
- `GET /users` - List all users
- `GET /users/<id>` - Get user by ID
- `POST /users` - Create a new user

## Example Requests

```bash
# Seed data
curl http://localhost:5000/seed

# List users
curl http://localhost:5000/users

# Get specific user (use ID from /users response)
curl http://localhost:5000/users/65b8f2e4a1b2c3d4e5f6g7h8

# Create user
curl -X POST http://localhost:5000/users \
  -H "Content-Type: application/json" \
  -d '{"name": "Dave", "email": "dave@example.com", "age": 28}'
```

## Troubleshooting

**MongoDB connection error:**
```bash
# Make sure MongoDB is running
docker ps  # Check if mongo container is running
docker start mongo  # Start if stopped
```

**Cassette not found:**
```bash
# List available cassettes
ls ./cassettes/2026-01-22/

# Use timetracer CLI
timetracer list --dir ./cassettes
```

## Next Steps

- Try with compressed cassettes: `TIMETRACER_COMPRESSION=gzip`
- View cassettes in dashboard: `timetracer dashboard --dir ./cassettes --open`
- Compare cassettes: `timetracer diff --a old.json --b new.json`
