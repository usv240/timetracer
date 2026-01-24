# PyMongo Integration

Record and replay MongoDB operations using PyMongo (synchronous driver).

---

## Overview

The PyMongo plugin enables Timetracer to capture synchronous MongoDB operations. This is perfect for Flask applications, Django projects, ETL scripts, and any Python code that uses synchronous MongoDB access.

**When to use PyMongo plugin:**
- Flask applications with MongoDB
- Django apps using MongoDB (non-async views)
- Data processing scripts
- Admin/CLI tools
- Batch jobs and ETL pipelines

**When to use Motor plugin instead:**
- FastAPI applications (async)
- Django async views
- Any async/await code

---

## Installation

```bash
# Install Timetracer with MongoDB support
pip install timetracer[motor]  # Includes both Motor and PyMongo

# Or install PyMongo separately
pip install timetracer pymongo
```

---

## Quick Start

### Basic Setup

```python
from flask import Flask, jsonify
from pymongo import MongoClient
from timetracer.integrations.flask import auto_setup
from timetracer.plugins import enable_pymongo

# Create Flask app with Timetracer
app = auto_setup(Flask(__name__))

# Enable PyMongo plugin
enable_pymongo()

# Connect to MongoDB
client = MongoClient('mongodb://localhost:27017')
db = client.myapp

@app.route('/users/<user_id>')
def get_user(user_id):
    # This query is automatically captured!
    user = db.users.find_one({"_id": user_id})
    return jsonify(user)
```

### Record Mode

```bash
# Record API requests with MongoDB operations
TIMETRACER_MODE=record python app.py

# Make request
curl http://localhost:5000/users/123

# Check cassette
ls ./cassettes/
```

### Replay Mode

```bash
# Replay without MongoDB running!
docker stop mongodb  # Stop database

TIMETRACER_MODE=replay \
  TIMETRACER_CASSETTE=./cassettes/GET__users_123.json \
  python app.py

curl http://localhost:5000/users/123
# Returns same data from cassette!
```

---

## Supported Operations

### Query Operations

| Operation | Example | Captured |
|-----------|---------|----------|
| `find()` | `db.users.find({"age": {"$gt": 18}})` | Cursor creation |
| `find_one()` | `db.users.find_one({"email": "user@example.com"})` | Query + result |
| `count_documents()` | `db.users.count_documents({"active": true})` | Count result |
| `aggregate()` | `db.users.aggregate([{"$match": {...}}])` | Pipeline stages |

### Insert Operations

| Operation | Example | Captured |
|-----------|---------|----------|
| `insert_one()` | `db.users.insert_one({"name": "Alice"})` | Document + inserted_id |
| `insert_many()` | `db.users.insert_many([{...}, {...}])` | Count + inserted_ids |

### Update Operations

| Operation | Example | Captured |
|-----------|---------|----------|
| `update_one()` | `db.users.update_one(filter, {"$set": {...}})` | Match/modified counts |
| `update_many()` | `db.users.update_many(filter, update)` | Match/modified counts |
| `replace_one()` | `db.users.replace_one(filter, new_doc)` | Match/modified counts |

### Delete Operations

| Operation | Example | Captured |
|-----------|---------|----------|
| `delete_one()` | `db.users.delete_one({"_id": "123"})` | Deleted count |
| `delete_many()` | `db.users.delete_many({"inactive": true})` | Deleted count |

---

## Usage Examples

### Flask Application

```python
from flask import Flask, request, jsonify
from pymongo import MongoClient
from timetracer.integrations.flask import auto_setup
from timetracer.plugins import enable_pymongo

app = auto_setup(Flask(__name__))
enable_pymongo()

client = MongoClient('mongodb://localhost:27017')
db = client.shop

@app.route('/products', methods=['GET'])
def list_products():
    """List all products."""
    products = list(db.products.find({"in_stock": True}))
    
    # Convert ObjectId to string for JSON
    for product in products:
        product['_id'] = str(product['_id'])
    
    return jsonify({"products": products})

@app.route('/products', methods=['POST'])
def create_product():
    """Create a new product."""
    data = request.get_json()
    
    result = db.products.insert_one({
        "name": data['name'],
        "price": data['price'],
        "in_stock": True
    })
    
    return jsonify({
        "product_id": str(result.inserted_id),
        "created": True
    }), 201

if __name__ == '__main__':
    app.run(debug=True)
```

### Django View

```python
# views.py
from django.http import JsonResponse
from pymongo import MongoClient
from timetracer.plugins import enable_pymongo

# Enable once at startup
enable_pymongo()

client = MongoClient('mongodb://localhost:27017')
db = client.blog

def post_list(request):
    """List blog posts."""
    posts = list(db.posts.find({"published": True}))
    
    for post in posts:
        post['_id'] = str(post['_id'])
    
    return JsonResponse({"posts": posts})

def post_detail(request, post_id):
    """Get single post."""
    post = db.posts.find_one({"_id": post_id})
    
    if not post:
        return JsonResponse({"error": "Not found"}, status=404)
    
    post['_id'] = str(post['_id'])
    return JsonResponse(post)
```

### Data Processing Script

```python
# etl_script.py
from pymongo import MongoClient
from timetracer.plugins import enable_pymongo
from timetracer import TraceConfig
import os

# Enable PyMongo recording
enable_pymongo()

# Configure Timetracer for script mode
os.environ['TIMETRACER_MODE'] = 'record'
os.environ['TIMETRACER_CASSETTE_DIR'] = './etl_cassettes'

client = MongoClient('mongodb://localhost:27017')
source_db = client.source
target_db = client.target

def migrate_users():
    """Migrate users from source to target."""
    # Fetch all users from source
    users = list(source_db.users.find({}))
    print(f"Found {len(users)} users")
    
    # Transform data
    transformed = []
    for user in users:
        transformed.append({
            "user_id": user['_id'],
            "email": user['email'],
            "migrated_at": datetime.now()
        })
    
    # Insert into target
    result = target_db.migrated_users.insert_many(transformed)
    print(f"Migrated {len(result.inserted_ids)} users")

if __name__ == '__main__':
    migrate_users()
```

---

## Cassette Format

### Example Cassette

```json
{
  "schema_version": "1.0",
  "session": {
    "id": "abc123",
    "recorded_at": "2026-01-22T14:00:00Z",
    "service": "myapp",
    "env": "production"
  },
  "request": {
    "method": "GET",
    "path": "/users/123"
  },
  "events": [
    {
      "eid": 1,
      "event_type": "db.query",
      "start_offset_ms": 10.5,
      "duration_ms": 2.3,
      "signature": {
        "lib": "pymongo",
        "method": "FIND_ONE",
        "url": "myapp.users",
        "query": {
          "filter_keys": ["_id"]
        },
        "body_hash": "a1b2c3..."
      },
      "result": {
        "status": 0,
        "body": {
          "captured": true,
          "data": {
            "_id": "123",
            "name": "Alice",
            "email": "alice@example.com",
            "age": 30
          }
        }
      }
    }
  ]
}
```

### Signature Fields

- **lib**: Always `"pymongo"`
- **method**: Operation name (FIND_ONE, INSERT_ONE, UPDATE_ONE, etc.)
- **url**: Format: `{database}.{collection}`
- **query**: Filter keys (for matching)
- **body_hash**: Hash of filter + update documents

---

## Configuration

### Enable/Disable

```python
from timetracer.plugins import enable_pymongo, disable_pymongo

# Enable PyMongo recording
enable_pymongo()

# Use PyMongo normally
db.users.find_one({"email": "user@example.com"})

# Disable when done (optional)
disable_pymongo()
```

### Multiple Databases

```python
from pymongo import MongoClient
from timetracer.plugins import enable_pymongo

enable_pymongo()  # Applies to ALL PyMongo operations

# Works with multiple databases/clients
client1 = MongoClient('mongodb://localhost:27017')
client2 = MongoClient('mongodb://remote:27017')

db1 = client1.primary
db2 = client2.analytics

# Both captured
db1.users.find_one({"_id": "123"})      # Captured
db2.events.insert_one({"type": "log"})  # Also captured
```

### Compression

```python
# Use compression for MongoDB-heavy applications
import os

os.environ['TIMETRACER_MODE'] = 'record'
os.environ['TIMETRACER_COMPRESSION'] = 'gzip'

# Cassettes will be saved as .json.gz
# Typical reduction: 60-95% smaller
```

---

## Testing with pytest

### Using Fixtures

```python
# test_users.py
import pytest
from pymongo import MongoClient
from timetracer.plugins import enable_pymongo

def test_get_user_from_cassette(timetracer_replay):
    """Test user retrieval with replayed MongoDB."""
    enable_pymongo()
    
    # Replay from cassette
    with timetracer_replay("GET__users_123.json"):
        client = MongoClient('mongodb://fake:27017')  # Won't actually connect
        db = client.myapp
        
        # This returns data from cassette!
        user = db.users.find_one({"_id": "123"})
        
        assert user['name'] == "Alice"
        assert user['email'] == "alice@example.com"


def test_create_user_recorded(timetracer_record):
    """Test user creation with recording."""
    enable_pymongo()
    
    with timetracer_record() as cassette_path:
        client = MongoClient('mongodb://localhost:27017')
        db = client.testdb
        
        # This is recorded
        result = db.users.insert_one({
            "name": "Bob",
            "email": "bob@example.com"
        })
        
        assert result.inserted_id is not None
    
    # Cassette saved at cassette_path
    print(f"Cassette saved: {cassette_path}")
```

---

## Troubleshooting

### Issue: MongoDB Operations Not Captured

**Problem:** PyMongo operations are not appearing in cassettes.

**Solution:**
1. Ensure `enable_pymongo()` is called before any MongoDB operations
2. Check that Timetracer mode is set to `record`
3. Verify a session is active (middleware creates sessions automatically)

```python
# Correct order
enable_pymongo()
client = MongoClient(...)
db.users.find_one(...)  # Captured

# Wrong order
client = MongoClient(...)
db.users.find_one(...)  # NOT captured
enable_pymongo()  # Too late!
```

### Issue: ObjectId Serialization Error

**Problem:** `Object of type ObjectId is not JSON serializable`

**Solution:** The plugin automatically handles ObjectIds. If you see this error, you're likely serializing manually. Let Timetracer handle it:

```python
# Don't do this
user = db.users.find_one({"_id": "123"})
return jsonify(user)  # Error!

# Do this
user = db.users.find_one({"_id": "123"})
if user:
    user['_id'] = str(user['_id'])  # Convert to string
return jsonify(user)
```

### Issue: Replay Fails with Connection Error

**Problem:** Replay mode tries to connect to MongoDB.

**Solution:** This might happen if `enable_pymongo()` wasn't called, or if code bypasses the plugin. Ensure:

```python
# Call this BEFORE creating MongoDB client
enable_pymongo()

# Then create client
client = MongoClient(...)
```

### Issue: Slow Performance in Record Mode

**Problem:** Recording is noticeably slower.

**Solution:** This is normal - each operation is being tracked. To reduce impact:

1. Use sampling:
```bash
TIMETRACER_SAMPLE_RATE=0.1  # Record only 10% of requests
```

2. Record only errors:
```bash
TIMETRACER_ERRORS_ONLY=true  # Only record failed requests
```

3. Use compression:
```bash
TIMETRACER_COMPRESSION=gzip  # Smaller files = faster I/O
```

---

## Best Practices

### 1. Enable Early

```python
# Enable PyMongo before creating any MongoDB connections
enable_pymongo()

# Then create connections
client = MongoClient(...)
```

### 2. Use with Flask/Django Middleware

Let the framework middleware handle session management:

```python
# Flask
app = auto_setup(Flask(__name__))
enable_pymongo()  # Just enable, middleware handles the rest

# Django  
# settings.py
MIDDLEWARE = ['timetracer.integrations.django.TimeTracerMiddleware', ...]
```

### 3. Handle ObjectIds for JSON

Always convert ObjectIds to strings when returning JSON:

```python
user = db.users.find_one({"_id": user_id})
if user:
    user['_id'] = str(user['_id'])
return jsonify(user)
```

### 4. Use Compression for Large Datasets

If you're querying large documents:

```bash
TIMETRACER_MODE=record \
TIMETRACER_COMPRESSION=gzip \
python app.py
```

### 5. Test with Cassettes

Create integration tests using recorded cassettes:

```python
def test_user_workflow(timetracer_replay):
    """Test complete user workflow."""
    enable_pymongo()
    
    with timetracer_replay("user_workflow.json"):
        # All MongoDB operations replay from cassette
        # No actual database needed!
        result = create_user("Alice")
        user = get_user(result['user_id'])
        update_user(user['_id'], {"status": "active"})
```

---

## Comparison: PyMongo vs Motor

| Feature | PyMongo | Motor |
|---------|---------|-------|
| **Type** | Synchronous | Asynchronous |
| **Best for** | Flask, Django sync, scripts | FastAPI, Django async |
| **Syntax** | `db.users.find_one()` | `await db.users.find_one()` |
| **Compatibility** | All Python code | async/await only |
| **When to use** | Traditional apps, ETL | Modern async apps |

**Use both:** If you have mixed sync/async code, enable both plugins:

```python
from timetracer.plugins import enable_pymongo, enable_motor

enable_pymongo()  # For sync code
enable_motor()    # For async code
```

---

## See Also

- [Motor (Async MongoDB) Integration](motor.md)
- [Flask Integration](flask.md)
- [Django Integration](django.md)
- [pytest Plugin](pytest.md)
- [Cassette Compression](compression.md)

---

## Questions?

- **GitHub Issues:** https://github.com/usv240/timetracer/issues
- **Documentation:** https://github.com/usv240/timetracer#readme
- **Examples:** See `examples/pymongo_flask_app/`
