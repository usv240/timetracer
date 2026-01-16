# Flask + httpx Example

This example demonstrates Timetrace with Flask and httpx.

## Setup

```bash
pip install timetrace[flask,httpx]
```

## Run in Record Mode

```bash
TIMETRACE_MODE=record TIMETRACE_DIR=./cassettes python app.py
```

Then make requests:
```bash
curl http://localhost:5000/weather/london
curl -X POST http://localhost:5000/checkout
```

Cassettes will be saved to `./cassettes/`.

## Run in Replay Mode

```bash
TIMETRACE_MODE=replay TIMETRACE_CASSETTE=./cassettes/.../GET__weather.json python app.py
```

The httpx calls will be mocked from the cassette - no network requests made!

## Features Demonstrated

- Flask middleware integration
- httpx outbound call recording
- Deterministic replay with mocked dependencies
- Terminal summaries
