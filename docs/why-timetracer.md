# Why Timetracer?

**Time-travel debugging for Python web applications.**

> Record once. Replay anywhere. Debug faster.

---

## Overview

Timetracer is a production-grade debugging tool that captures API requests with all their dependencies and enables deterministic replay anywhere—locally, in CI/CD, or offline. Unlike traditional mocking tools that only capture HTTP, Timetracer records your entire dependency chain: HTTP calls, database queries, and cache operations.

---

## Key Advantages

### Multi-Dependency Capture

**The only tool that captures everything in a single cassette:**

| Dependency Type | Captured |
|-----------------|----------|
| Incoming HTTP requests | Yes |
| Outgoing HTTP calls (httpx, requests) | Yes |
| Database queries (SQLAlchemy) | Yes |
| Cache operations (Redis) | Yes |
| Error stack traces | Yes |

**Why it matters:** Competitors only capture HTTP. To achieve what Timetracer does, you would need 3+ separate tools configured and synchronized together.

---

### Zero-Configuration Setup

**Add two lines of code. Done.**

```python
from timetracer.integrations.fastapi import auto_setup
app = auto_setup(FastAPI())
```

No test decorators. No manual stub configuration. No proxy setup. The middleware automatically captures everything.

**Competitor approach:**
- VCR.py: Decorate every test function individually
- WireMock: Configure stubs, matchers, and response templates
- Hoverfly: Set up proxy infrastructure and middleware

---

### Production-First Design

**Built for production debugging, not just testing.**

```bash
# Record from real production traffic
TIMETRACER_MODE=record uvicorn app:app

# Replay exact scenario locally
TIMETRACER_MODE=replay TIMETRACER_CASSETTE=error.json uvicorn app:app
```

**Use cases:**
- Reproduce production bugs on your laptop
- Debug without access to production databases
- Work offline with pre-recorded data
- Create demos that work without external services

**Competitor approach:** Most tools are designed for test-time mocking, not production capture.

---

### Interactive Dashboard

**Visual debugging interface with real-time replay.**

```bash
# Static HTML dashboard
timetracer dashboard --dir ./cassettes --open

# Live server with one-click replay
timetracer serve --dir ./cassettes --open
```

**Dashboard features:**
- Sortable table (time, method, endpoint, status, duration)
- Advanced filters (method, status, duration, time range)
- Error highlighting with visual indicators
- Full Python stack traces for errors
- Dependency waterfall visualization
- One-click replay from browser
- Raw JSON with syntax highlighting

**Competitor approach:** Terminal output only. No visual interface.

---

### Hybrid Replay Mode

**Mock some dependencies. Keep others live.**

```bash
# Mock database and cache, keep external API live
TIMETRACER_MOCK_PLUGINS=sqlalchemy,redis \
TIMETRACER_LIVE_PLUGINS=httpx \
uvicorn app:app
```

**Use cases:**
- Test with fresh external API data while avoiding database mutations
- Isolate specific components for debugging
- Gradually migrate from mocked to live dependencies

**Competitor approach:** All-or-nothing mocking. Either everything is mocked or nothing is.

---

### Cloud Storage Support

**Share cassettes across teams with S3 integration.**

```bash
TIMETRACER_S3_BUCKET=my-cassettes \
TIMETRACER_S3_PREFIX=production/ \
uvicorn app:app
```

**Benefits:**
- CI/CD pipeline integration
- Team collaboration on bug reproduction
- Centralized cassette management
- Production bug triage workflows

**Competitor approach:** Local filesystem storage only.

---

### Security by Default

**Automatic sensitive data protection.**

Built-in redaction for:
- `Authorization` headers
- `Cookie` and `Set-Cookie` headers
- Password fields in request/response bodies
- API keys and tokens
- Configurable body size limits (64KB default)

**Competitor approach:** Manual filter configuration. Miss one field and your secrets are in version control.

---

### Comparison Tools

**Built-in diff engine for regression detection.**

```bash
# Compare two cassettes
timetracer diff --a baseline.json --b current.json
```

**Output includes:**
- Response body differences
- Status code changes
- Header modifications
- Timing variations

**Use cases:**
- Detect behavior changes between releases
- Identify performance regressions
- Validate bug fixes

---

### Timeline Visualization

**Dependency waterfall charts for performance analysis.**

```bash
timetracer timeline ./cassette.json --open
```

**Visualizes:**
- Request lifecycle timing
- External HTTP call duration
- Database query execution time
- Cache operation latency
- Parallel vs sequential operations

---

## Framework Support

| Framework | Integration |
|-----------|-------------|
| **FastAPI** | Native middleware with async support |
| **Flask** | Native middleware |
| **HTTPX** | Async and sync client recording |
| **Requests** | Full request/response capture |
| **SQLAlchemy** | Query capture with parameters |
| **Redis** | Command capture with responses |

---

## Competitive Comparison

| Feature | Timetracer | VCR.py | Betamax | WireMock | Hoverfly |
|---------|-----------|--------|---------|----------|----------|
| HTTP Recording | Yes | Yes | Yes | Yes | Yes |
| Database Recording | Yes | No | No | No | No |
| Redis Recording | Yes | No | No | No | No |
| FastAPI Middleware | Yes | No | No | No | No |
| Flask Middleware | Yes | No | No | No | No |
| Interactive Dashboard | Yes | No | No | No | No |
| Stack Trace Capture | Yes | No | No | No | No |
| Hybrid Replay | Yes | No | No | Partial | Partial |
| S3 Storage | Yes | No | No | No | No |
| Diff Tool | Yes | No | No | No | No |
| Timeline Visualization | Yes | No | No | No | No |
| Auto Redaction | Yes | Manual | Manual | Manual | Manual |
| Zero-Config Setup | Yes | No | No | No | No |
| Python Native | Yes | Yes | Yes | No (Java) | No (Go) |
| Production Capture | Yes | No | No | No | Partial |

---

## Common Use Cases

### 1. Production Bug Reproduction

**Problem:** A bug occurs in production but cannot be reproduced locally.

**Solution:**
```bash
# Cassette already recorded in production
timetracer show ./cassettes/error_20260116.json

# Replay exact scenario locally
TIMETRACER_MODE=replay TIMETRACER_CASSETTE=error_20260116.json uvicorn app:app
curl http://localhost:8000/api/users/123  # Same error, locally
```

### 2. Offline Development

**Problem:** External APIs are unavailable or rate-limited during development.

**Solution:**
```bash
# Record once when API is available
TIMETRACER_MODE=record python test_scenarios.py

# Develop offline indefinitely
TIMETRACER_MODE=replay uvicorn app:app
```

### 3. Regression Testing

**Problem:** Need to verify that code changes don't break existing behavior.

**Solution:**
```bash
# Record baseline
TIMETRACER_MODE=record pytest tests/

# After code changes, compare
timetracer diff --a baseline.json --b current.json
```

### 4. Customer Demos

**Problem:** Demo environment depends on external services that may be unreliable.

**Solution:**
```bash
# Pre-record demo scenarios
TIMETRACER_MODE=record python record_demo.py

# Demo works anywhere, anytime
TIMETRACER_MODE=replay uvicorn app:app
```

### 5. Performance Analysis

**Problem:** Need to identify slow dependencies in a request.

**Solution:**
```bash
# Generate timeline
timetracer timeline ./slow_request.json --open

# View waterfall chart showing:
# - 50ms DB query
# - 200ms external API call
# - 10ms Redis lookup
```

---

## Configuration Reference

| Variable | Description | Default |
|----------|-------------|---------|
| `TIMETRACER_MODE` | Operating mode: `off`, `record`, `replay` | `off` |
| `TIMETRACER_DIR` | Cassette storage directory | `./cassettes` |
| `TIMETRACER_CASSETTE` | Cassette file path for replay | — |
| `TIMETRACER_SAMPLE_RATE` | Fraction of requests to record (0.0-1.0) | `1.0` |
| `TIMETRACER_ERRORS_ONLY` | Only record error responses | `false` |
| `TIMETRACER_MOCK_PLUGINS` | Plugins to mock during replay | all |
| `TIMETRACER_LIVE_PLUGINS` | Plugins to keep live during replay | none |
| `TIMETRACER_S3_BUCKET` | S3 bucket for cassette storage | — |
| `TIMETRACER_S3_PREFIX` | S3 key prefix for cassettes | — |

---

## CLI Commands

```bash
# List recorded cassettes
timetracer list --dir ./cassettes

# Show cassette details
timetracer show ./cassette.json

# Compare cassettes
timetracer diff --a old.json --b new.json

# Generate timeline visualization
timetracer timeline ./cassette.json --open

# Generate static dashboard
timetracer dashboard --dir ./cassettes --open

# Start live dashboard server
timetracer serve --dir ./cassettes --port 8080 --open
```

---

## Installation

```bash
# Full installation
pip install timetracer[all]

# Selective installation
pip install timetracer[fastapi,httpx]      # FastAPI + HTTP
pip install timetracer[flask,requests]     # Flask + HTTP
pip install timetracer[sqlalchemy,redis]   # Database + Cache
```

---

## Summary

Timetracer is the most comprehensive time-travel debugging tool for Python web applications:

| Capability | Benefit |
|------------|---------|
| **Multi-dependency capture** | Single cassette contains HTTP, DB, Redis |
| **Zero-config middleware** | Add two lines, capture everything |
| **Production-first design** | Debug production bugs locally |
| **Interactive dashboard** | Visual debugging with one-click replay |
| **Hybrid replay** | Fine-grained control over mocking |
| **Cloud storage** | Team collaboration via S3 |
| **Security by default** | Automatic sensitive data redaction |
| **Comparison tools** | Diff and timeline for analysis |

**Record once. Replay anywhere. Debug faster.**

---

## Resources

- [Quick Start Guide](quickstart.md)
- [Configuration Reference](configuration.md)
- [Dashboard Guide](dashboard.md)
- [Plugin Guide](plugins.md)
- [Security Best Practices](security.md)
- [GitHub Repository](https://github.com/usv240/timetracer)
- [PyPI Package](https://pypi.org/project/timetracer/)
