# Release Notes

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
