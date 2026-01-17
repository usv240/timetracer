# Release Notes

## v1.1.0 - Dashboard Release (2026-01-16)

### 🎯 Highlights

This release introduces the **Interactive Dashboard** - a powerful web interface for browsing, filtering, and debugging your recorded cassettes.

### ✨ New Features

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
- **Slow request warning** - Duration >1s shows ⚠ warning icon
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

### 🔧 Improvements

- **Error row highlighting** - CSS styling for error rows
- **Slow warning indicator** - Visual warning for slow requests
- **Custom time range** - Date/time picker for filtering
- **Replay button** in table rows for quick access
- **Syntax-highlighted JSON** in raw data view

### 📚 Documentation

- Added [Dashboard Guide](docs/dashboard.md)
- Updated README with dashboard section
- Added CLI examples for dashboard commands

### 🐛 Bug Fixes

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
