# Flask + httpx Example

Complete example of Timetracer with Flask and httpx.

## Quick Start

### 1. Install

```bash
pip install timetracer[flask,httpx]
```

### 2. Run in Record Mode

```bash
cd examples/flask_httpx
TIMETRACER_MODE=record python app.py
```

### 3. Make Requests

```bash
# Weather endpoint (external API call)
curl http://localhost:5000/weather/london

# Checkout endpoint (external API call)
curl -X POST http://localhost:5000/checkout
```

Check `./cassettes/` for saved recordings.

### 4. Replay

```bash
# List cassettes
timetracer list --dir ./cassettes

# Replay
TIMETRACER_MODE=replay \
TIMETRACER_CASSETTE=./cassettes/GET__weather__abc123.json \
python app.py

# Same request - external calls mocked!
curl http://localhost:5000/weather/london
```

## Files

| File | Description |
|------|-------------|
| `app.py` | Flask app with httpx calls |
| `cassettes/` | Saved recordings |

## How It Works

1. **Middleware** wraps Flask's WSGI app
2. **httpx plugin** intercepts outbound HTTP calls
3. **Record mode** saves everything to JSON cassettes
4. **Replay mode** mocks external calls from cassettes

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TIMETRACER_MODE` | off | `record`, `replay`, or `off` |
| `TIMETRACER_DIR` | ./cassettes | Where to save cassettes |
| `TIMETRACER_CASSETTE` | - | Cassette file for replay |
