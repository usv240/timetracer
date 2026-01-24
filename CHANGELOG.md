# Changelog

All notable changes to Timetracer will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.6.0] - 2026-01-24

### Added
- **PyMongo Plugin**: Synchronous MongoDB support
  - Support for all CRUD operations: `find_one`, `insert_one`, `update_one`, `delete_one`, etc.
  - Support for `insert_many`, `update_many`, `delete_many`, `replace_one`
  - Support for `count_documents` and `aggregate` pipelines
  - Automatic ObjectId and DateTime serialization
  - Perfect for Flask apps, Django sync views, ETL scripts
  - Integration with pytest fixtures
- **Starlette Integration**: Lightweight ASGI framework support
  - Complete middleware integration (reuses FastAPI's ASGI middleware)
  - `auto_setup()` helper function for one-line configuration
  - Full support for all Timetracer features (record, replay, plugins)
  - Async/await support with httpx plugin
  - Path parameters, query parameters, and headers capture
  - Identical API to FastAPI integration (since FastAPI is built on Starlette)
  - Zero overhead - just 84 lines of code!
- **New Examples**:
  - `examples/pymongo_flask_app/` - Flask + PyMongo integration example
  - `examples/starlette_example/` - Starlette + httpx + GitHub API example
- **New Documentation**:
  - `docs/pymongo.md` - Comprehensive PyMongo guide
  - `docs/starlette.md` - Comprehensive Starlette guide
  
### Changed
- Updated README.md to include PyMongo and Starlette in features
- Enhanced MongoDB coverage: Now supports both sync (PyMongo) and async (Motor)
- Enhanced framework support: FastAPI, Starlette, Flask, Django
- Test suite expanded to 170 tests (up from 149)
- Updated `pyproject.toml` to mention Starlette in description and keywords

### Technical
- 15 new unit tests for PyMongo plugin
- 10 new integration tests for Starlette
- 100% test pass rate maintained
- Zero breaking changes

## [1.5.0] - 2026-01-22

### Added
- **Cassette Compression**: Gzip compression support with 60-95% size reduction
  - New `TIMETRACER_COMPRESSION` environment variable
  - New `CompressionType` enum (`NONE`, `GZIP`)
  - Automatic detection of `.json.gz` files
  - Transparent read/write of compressed cassettes
- **Motor/MongoDB Plugin**: Full async MongoDB support
  - Support for `find_one`, `insert_one`, `update_one`, `delete_one`, etc.
  - Automatic ObjectId and DateTime serialization
  - Integration with pytest fixtures
  - Sensitive field redaction
- **New Examples**:
  - `examples/compression_example/` - Compression demo with comparison script
  - `examples/motor_mongodb/` - Motor/MongoDB integration example
- **New Documentation**:
  - `docs/compression.md` - Comprehensive compression guide
  - `docs/motor.md` - Motor/MongoDB integration guide

### Changed
- Bumped version from 1.4.0 to 1.5.0
- Updated README.md with compression and Motor features
- Enhanced test suite (149 tests, 100% passing)

### Fixed
- Windows path escaping in dashboard JavaScript
- Improved error messages for missing cassettes
- Enhanced serialization for MongoDB data types

## [1.4.0] - 2026-01-19

### Added
- **Django Integration**: Full middleware support for Django 3.2+
  - Sync and async view support
  - Django REST Framework compatibility
  - Configuration via settings.py or environment variables
- **pytest Plugin**: Zero-config fixtures for cassette-based testing
  - `timetracer_replay` fixture for replay mode
  - `timetracer_record` fixture for record mode
  - `timetracer_auto` fixture for auto-select mode
  - `cassette_dir` fixture for cassette directory access
- **New Examples**:
  - `examples/django_app/` - Django integration example
  - `examples/pytest_example/` - pytest fixtures example
- **New Documentation**:
  - `docs/django.md` - Django integration guide
  - `docs/pytest.md` - pytest plugin guide

### Changed
- Updated README with Django installation instructions
- Enhanced documentation structure

## [1.3.0] - 2026-01-18

### Added
- **aiohttp Plugin**: Full support for aiohttp async HTTP client
  - Request body capture (data, json parameters)
  - Response body capture and replay
  - Query parameter handling
  - Error recording and replay
- **CI/CD Integration Guides**:
  - ArgoWorkflows guide
  - GitHub Actions guide
- **New Example**: `examples/fastapi_aiohttp/`
- **New Documentation**: aiohttp plugin documentation

### Changed
- Renamed `TimeTraceMiddleware` to `TimeTracerMiddleware` (backward compatible alias)
- Updated `auto_setup()` to support `"aiohttp"` in plugins list

## [1.2.0] - 2026-01-17

### Added
- **Enhanced Security**: Comprehensive sensitive data detection
  - Expanded from 10 to 100+ sensitive key patterns
  - PII pattern detection (email, phone, SSN, credit card, IP)
  - Financial data protection (PCI-DSS compliance)
  - Healthcare data protection (HIPAA compliance)
- **New APIs**:
  - `detect_pii()` - Detect PII type in values
  - `redact_pii_in_text()` - Redact all PII in unstructured text
- **Enhanced Header Protection**:
  - `x-refresh-token`, `x-session-token`
  - `x-csrf-token`, `x-xsrf-token`
  - `proxy-authorization`, `www-authenticate`
  - `x-client-secret`, `x-secret-key`

### Changed
- Updated Security Guide with comprehensive coverage tables
- Added PII detection examples

### Fixed
- Credit card detection now includes Luhn algorithm validation

## [1.1.0] - 2026-01-16

### Added
- **Interactive Dashboard**: Web interface for browsing cassettes
  - Sortable table (time, method, endpoint, status, duration)
  - Advanced filters (endpoint, method, status, duration, time range)
  - Error highlighting with red rows
  - Slow request warnings (>1s)
  - View details modal with request/response/errors
  - Raw JSON with syntax highlighting
- **Live Server**: Real-time dashboard with replay functionality
  - `timetracer serve` command
  - Live replay from UI
  - API endpoints for integration
- **Stack Trace Capture**: Full Python traceback for errors
- **New Documentation**: `docs/dashboard.md`

### Fixed
- Windows path escaping in JavaScript
- Modal click handlers for View/Replay buttons

## [1.0.2] - 2026-01-16

### Changed
- **Breaking**: Environment variables renamed from `TIMETRACE_*` to `TIMETRACER_*`
- All S3 variables now use `TIMETRACER_S3_*` prefix

### Migration
Update environment variables:
- `TIMETRACE_MODE` → `TIMETRACER_MODE`
- `TIMETRACE_DIR` → `TIMETRACER_DIR`
- `TIMETRACE_S3_BUCKET` → `TIMETRACER_S3_BUCKET`

## [1.0.0] - 2026-01-15

### Added
Initial release with core features:
- FastAPI and Flask middleware integration
- HTTPX and Requests plugins for HTTP capture
- SQLAlchemy plugin for database queries
- Redis plugin for cache commands
- Cassette recording and replay
- CLI tools (list, show, diff, timeline)
- S3 storage support
- Hybrid replay (mock some, live others)
- Automatic sensitive data redaction

[1.6.0]: https://github.com/usv240/timetracer/compare/v1.5.0...v1.6.0
[1.5.0]: https://github.com/usv240/timetracer/compare/v1.4.0...v1.5.0
[1.4.0]: https://github.com/usv240/timetracer/compare/v1.3.0...v1.4.0
[1.3.0]: https://github.com/usv240/timetracer/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/usv240/timetracer/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/usv240/timetracer/compare/v1.0.2...v1.1.0
[1.0.2]: https://github.com/usv240/timetracer/compare/v1.0.0...v1.0.2
[1.0.0]: https://github.com/usv240/timetracer/releases/tag/v1.0.0
