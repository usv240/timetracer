# Release Notes

## v1.5.0 - Compression + Motor/MongoDB Support (2026-01-22)

### Highlights

Two major features that significantly enhance Timetracer's capabilities: **cassette compression** for reduced storage costs and **Motor/MongoDB** plugin for async database support.

### Cassette Compression

Gzip compression support with automatic size reduction of 60-95%:

```bash
# Enable compression via environment variable
export TIMETRACER_COMPRESSION=gzip
TIMETRACER_MODE=record uvicorn app:app

# Or via code
from timetracer import TraceConfig, CompressionType

config = TraceConfig(
    mode="record",
    compression=CompressionType.GZIP,
)
```

**Features:**
- **60-95% size reduction** - Tested with real-world cassettes
- **Transparent read** - Auto-detection of `.json.gz` files
- **Zero config replay** - Replay works seamlessly with compressed cassettes
- **Environment variable control** - `TIMETRACER_COMPRESSION=gzip` or `none`
- **File extension support** - `.json` for uncompressed, `.json.gz` for compressed

**Benefits:**
- Smaller git repositories with committed cassettes
- Faster CI/CD artifact upload/download
- Reduced storage costs for large test suites
- Safe to commit compressed cassettes to public repos

**Example:**
```bash
# Uncompressed: 44,662 bytes
# Compressed:    1,915 bytes (95.7% reduction)
timetracer dashboard --dir ./cassettes --open
```

**Install:**
```bash
pip install timetracer  # Compression included in core package
```

### Motor/MongoDB Plugin

Full async MongoDB support via the Motor driver:

```python
from motor.motor_asyncio import AsyncIOMotorClient
from timetracer.plugins import enable_motor

enable_motor()

client = AsyncIOMotorClient("mongodb://localhost:27017")
db = client.mydb

# These operations are automatically captured
await db.users.insert_one({"name": "Alice", "age": 30})
user = await db.users.find_one({"name": "Alice"})
```

**Supported Operations:**
- `find_one` - Single document query
- `insert_one` / `insert_many` - Document insertion
- `update_one` / `update_many` - Document updates
- `delete_one` / `delete_many` - Document deletion
- `count_documents` - Count operations
- `aggregate` - Aggregation pipelines
- `find` - Cursor creation

**Features:**
- Full async/await support
- Automatic ObjectId serialization
- DateTime handling
- Sensitive field redaction (password, token, etc.)
- Error capture and replay
- Integration with pytest fixtures

**Cassette Format:**
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

**Install:**
```bash
pip install timetracer[motor]
```

### Testing & Quality

All features have been thoroughly tested:
- ✅ **149/149 tests passing** (100% success rate)
- ✅ Compression tests: 3/3 passing
- ✅ Motor plugin tests: 13/13 passing
- ✅ Integration examples for all features
- ✅ Performance benchmarks included

### Documentation

New documentation added:
- `docs/compression.md` - Comprehensive compression guide
- `docs/motor.md` - Motor/MongoDB integration guide
- `examples/compression_example/` - Full compression example with comparison script
- `examples/motor_mongodb/` - Motor integration example

Updated documentation:
- README.md - Added compression and Motor features
- ROADMAP.md - Marked compression and Motor as completed
- Configuration reference - Added `TIMETRACER_COMPRESSION` variable

### Bug Fixes

- Fixed Windows path escaping in dashboard JavaScript
- Improved error messages for missing cassettes
- Enhanced serialization for MongoDB data types

### Breaking Changes

None. This release is fully backward compatible.

### Migration Guide

No migration needed. Existing cassettes continue to work. To enable compression for new recordings:

```bash
# Option 1: Environment variable
export TIMETRACER_COMPRESSION=gzip

# Option 2: Code configuration
config = TraceConfig(compression=CompressionType.GZIP)
```

---

## v1.4.0 - Django Support + pytest Plugin (2026-01-19)

### Highlights

Two major features: Django integration and a pytest plugin for cassette-based testing.

### Django Support

Full Django middleware supporting sync and async views:

```python
# settings.py
MIDDLEWARE = [
    'timetracer.integrations.django.TimeTracerMiddleware',
    # ...
]

TIMETRACER = {
    'MODE': 'record',
    'CASSETTE_DIR': './cassettes',
}
```

**Features:**
- Django 3.2 LTS and later
- Async views (Django 4.1+)
- Django REST Framework compatibility
- Configuration via settings.py or environment variables

**Install:**
```bash
pip install timetracer[django]
```

### pytest Plugin

Built-in pytest fixtures for cassette-based testing:

```python
def test_external_api(timetracer_replay, client):
    with timetracer_replay("my_test.json"):
        response = client.get("/api/users")
        assert response.status_code == 200
```

**Fixtures:**
- `timetracer_replay` - Replay from recorded cassettes
- `timetracer_record` - Record new cassettes
- `timetracer_auto` - Auto-select based on cassette existence

The plugin is auto-registered with pytest.

### Documentation

- Added `docs/django.md` - Django integration guide
- Added `docs/pytest.md` - pytest plugin guide
- Updated README with Django installation

---

## v1.3.0 - aiohttp Support (2026-01-18)

### Highlights

Added full support for **aiohttp** HTTP client, completing the trio of supported Python HTTP clients (httpx, requests, aiohttp).

### New Plugin: aiohttp

Record and replay aiohttp async HTTP client calls:

```python
from timetracer.plugins import enable_aiohttp, disable_aiohttp

enable_aiohttp()

async with aiohttp.ClientSession() as session:
    async with session.get("https://api.example.com/data") as resp:
        data = await resp.json()
```

**Features:**
- Full async support with `ClientSession`
- Request body capture (data, json parameters)
- Response body capture and replay
- Query parameter handling
- Error recording and replay
- Mock response with full `ClientResponse` interface

**Installation:**
```bash
pip install timetracer[aiohttp]
```

### Documentation

- Added aiohttp plugin documentation
- Added CI/CD integration guide (ArgoWorkflows, GitHub Actions)
- Updated README with aiohttp examples
- New example project: `examples/fastapi_aiohttp/`

### API Changes

- **Middleware renamed**: `TimeTraceMiddleware` is now `TimeTracerMiddleware`
  - Old name still works (backward compatible alias)
  - Update imports when convenient: `from timetracer.integrations.fastapi import TimeTracerMiddleware`

- **auto_setup()** now supports `"aiohttp"` in plugins list

---

## v1.2.0 - Enhanced Security (2026-01-17)

### Highlights

This release significantly enhances Timetracer's security capabilities with **comprehensive sensitive data detection** covering authentication, PII, financial data (PCI-DSS), and healthcare data (HIPAA).

### Security Enhancements

#### Enhanced Sensitive Key Detection

Expanded from 10 to **100+ sensitive key patterns** across these categories:

**Authentication & Credentials:**
- `password`, `passwd`, `pwd`, `secret`
- `token`, `api_key`, `access_token`, `refresh_token`
- `private_key`, `secret_key`, `signing_key`, `encryption_key`
- `csrf`, `xsrf`, `otp`, `mfa`, `pin`, `verification_code`

**Personal Identifiable Information (PII):**
- `ssn`, `social_security`, `passport`, `driver_license`
- `phone`, `mobile`, `email`, `email_address`
- `date_of_birth`, `dob`, `address`, `zip_code`

**Financial Data (PCI-DSS Compliance):**
- `credit_card`, `card_number`, `cvv`, `cvc`
- `bank_account`, `account_number`, `routing_number`
- `iban`, `swift`, `expiry`, `cardholder`

**Healthcare Data (HIPAA Compliance):**
- `patient_id`, `medical_record`, `diagnosis`
- `insurance_id`, `policy_number`, `provider_id`

#### New: PII Pattern Detection

Regex-based detection of PII patterns in string values:

| Pattern | Example | Redacted As |
|---------|---------|-------------|
| Email | `user@example.com` | `[REDACTED:EMAIL]` |
| Phone | `555-123-4567` | `[REDACTED:PHONE]` |
| SSN | `123-45-6789` | `[REDACTED:SSN]` |
| Credit Card | `4111-1111-1111-1111` | `[REDACTED:CREDIT_CARD]` |
| IPv4/IPv6 | `192.168.1.1` | `[REDACTED:IP]` |

Credit card detection includes **Luhn algorithm validation** to reduce false positives.

#### Enhanced Header Protection

Added protection for:
- `x-refresh-token`, `x-session-token`
- `x-csrf-token`, `x-xsrf-token`
- `proxy-authorization`, `www-authenticate`
- `x-client-secret`, `x-secret-key`

### New APIs

```python
from timetracer.policies import detect_pii, redact_pii_in_text

# Detect PII type in a value
pii_type = detect_pii("user@example.com")  # Returns "email"

# Redact all PII in unstructured text
clean_text = redact_pii_in_text("Contact john@example.com at 555-123-4567")
# Returns "Contact [REDACTED:EMAIL] at [REDACTED:PHONE]"
```

### Documentation

- Updated Security Guide with comprehensive coverage tables
- Added PII detection examples

---

## v1.1.0 - Dashboard Release (2026-01-16)

### Highlights

This release introduces the **Interactive Dashboard** - a powerful web interface for browsing, filtering, and debugging your recorded cassettes.

### New Features

#### Dashboard (`timetracer dashboard`)
- **Interactive HTML dashboard** for browsing all cassettes
- **Sortable table** - Sort by time, method, endpoint, status, duration
- **Advanced filters**:
  - Search by endpoint
  - Filter by HTTP method (GET, POST, PUT, DELETE)
  - Filter by status (Errors Only, Success Only)
  - Filter by duration (Slow >1s, Medium, Fast)
  - Filter by time range (Last 5 mins, 10 mins, 1 hour, or custom)
- **Error highlighting** - Red rows for 4xx/5xx errors with left border
- **Slow request warning** - Duration >1s shows warning icon
- **View details modal** with:
  - Request overview (method, endpoint, status, duration)
  - Dependency events (external HTTP, DB, Redis calls)
  - Error details with full Python stack trace
  - Replay command (copy to clipboard)
  - Raw JSON with syntax highlighting

#### Live Server (`timetracer serve`)
- **Real-time dashboard server** at localhost
- **Live replay** - Click replay to see full request/response
- **API endpoints** for integration:
  - `GET /` - Dashboard HTML
  - `GET /api/cassettes` - List all cassettes
  - `GET /api/cassette?path=...` - Get cassette details
  - `POST /api/replay` - Execute replay

#### Stack Trace Capture
- **error_info** field added to Cassette type
- Captures exception type, message, and full traceback
- Displayed in dashboard detail modal for debugging

### Improvements

- **Error row highlighting** - CSS styling for error rows
- **Slow warning indicator** - Visual warning for slow requests
- **Custom time range** - Date/time picker for filtering
- **Replay button** in table rows for quick access
- **Syntax-highlighted JSON** in raw data view

### Documentation

- Added [Dashboard Guide](docs/dashboard.md)
- Updated README with dashboard section
- Added CLI examples for dashboard commands

### Bug Fixes

- Fixed Windows path escaping in JavaScript
- Fixed modal click handlers for View/Replay buttons

---

## v1.0.2 - Naming Consistency (2026-01-16)

### Breaking Changes

- **Environment variables renamed** from `TIMETRACE_*` to `TIMETRACER_*`
- All S3 variables now use `TIMETRACER_S3_*` prefix

### Migration

Update your environment variables:
```bash
# Old → New
TIMETRACE_MODE → TIMETRACER_MODE
TIMETRACE_DIR → TIMETRACER_DIR
TIMETRACE_S3_BUCKET → TIMETRACER_S3_BUCKET
```

---

## v1.0.0 - Initial Release

### Features

- FastAPI and Flask middleware integration
- HTTPX and Requests plugins for HTTP capture
- SQLAlchemy plugin for database queries
- Redis plugin for cache commands
- Cassette recording and replay
- CLI tools (list, show, diff, timeline)
- S3 storage support
- Hybrid replay (mock some, live others)
- Automatic sensitive data redaction
