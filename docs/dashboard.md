# Dashboard Guide

The Timetracer Dashboard provides an interactive web interface to browse, filter, and debug your recorded cassettes.

## Quick Start

```bash
# Generate a static HTML dashboard
timetracer dashboard --dir ./cassettes --open

# Or start a live server with replay capability
timetracer serve --dir ./cassettes --open
```

---

## Static Dashboard (`dashboard`)

Generates a self-contained HTML file that you can open in any browser.

```bash
timetracer dashboard --dir ./cassettes --out dashboard.html --open
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--dir`, `-d` | `./cassettes` | Cassette directory to scan |
| `--out`, `-o` | `dashboard.html` | Output HTML file name |
| `--limit`, `-n` | `500` | Maximum cassettes to include |
| `--open` | — | Open in browser after generating |

**Features:**
- Works offline (single HTML file)
- No server required
- Replay button copies command to clipboard

---

## Live Dashboard (`serve`)

Starts a local web server with enhanced replay functionality.

```bash
timetracer serve --dir ./cassettes --port 8765 --open
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--dir`, `-d` | `./cassettes` | Cassette directory to serve |
| `--port`, `-p` | `8765` | Server port |
| `--open` | — | Open in browser after starting |

**Features:**
- Real-time replay shows full request/response data
- API endpoints for integration
- Auto-refreshes when cassettes change

---

## Dashboard Features

### Filters

| Filter | Description |
|--------|-------------|
| **Search** | Search by endpoint path |
| **Methods** | Filter by HTTP method (GET, POST, PUT, DELETE) |
| **Status** | Filter by status (Errors Only, Success Only) |
| **Duration** | Filter by response time (Slow >1s, Medium, Fast) |
| **Time Range** | Preset (Last 5 mins, 1 hour) or custom date range |

### Error Highlighting

- **Red row background** - Requests with 4xx/5xx status
- **Red left border** - Visual indicator of errors
- **Warning icon** - Slow requests (>1000ms)

### Detail Modal

Click "View" on any cassette to see:

1. **Request Overview**
   - Method, Endpoint, Status, Duration
   - When it was recorded
   - Filename

2. **Dependency Events**
   - External HTTP calls made
   - Database queries (SQLAlchemy)
   - Redis commands

3. **Error Details** (if error occurred)
   - Exception type (e.g., `ValueError`)
   - Error message
   - Full Python stack trace

4. **Replay Command**
   - Ready-to-copy command to replay this cassette

5. **Raw JSON**
   - Full cassette data with syntax highlighting

### Replay

**Static Dashboard:** Copies the replay command to clipboard:
```bash
TIMETRACER_MODE=replay TIMETRACER_CASSETTE="path/to/cassette.json" uvicorn app:app
```

**Live Dashboard:** Shows the replay result directly:
- Original request details
- Recorded response status and body
- Mocked dependencies

---

## API Endpoints (Live Server)

When running `timetracer serve`, these APIs are available:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Dashboard HTML |
| `/api/cassettes` | GET | List all cassettes as JSON |
| `/api/cassette?path=...` | GET | Get full cassette JSON |
| `/api/replay` | POST | Replay a cassette |

---

## Use Cases

### 1. Debugging Production Errors

```bash
# Find errors from the last hour
timetracer dashboard --dir ./cassettes --open
# Filter: Errors Only + Last 1 hour
# Click on error, view stack trace
```

### 2. Performance Analysis

```bash
# Find slow requests
timetracer dashboard --dir ./cassettes --open
# Filter: Duration > Slow (>1s)
# Review dependency timing
```

### 3. Demo/Presentation

```bash
# Generate static dashboard for sharing
timetracer dashboard --dir ./demo-cassettes --out demo.html
# Share demo.html with team
```

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Escape` | Close detail modal |
| `Enter` | Focus search input |

---

## Customization

The dashboard HTML is self-contained. To customize:

1. Generate the dashboard
2. Edit the CSS/JavaScript in the HTML file
3. Or modify `src/timetracer/dashboard/template.py`

---

## Troubleshooting

### Dashboard shows "No cassettes found"

- Check the directory path is correct
- Ensure cassettes are `.json` files
- Verify files are readable

### Live replay stuck on "Loading..."

- Check browser console for errors
- Verify the cassette path exists
- Ensure the server is running

### Stack traces not showing

- Stack traces only appear when exceptions are captured
- Ensure your middleware catches and records exceptions
- Check `error_info` field in cassette JSON
