# Flask Integration

Use Timetrace with Flask applications.

## Installation

```bash
pip install timetrace[flask]
```

## Usage

### Option 1: WSGI Middleware

```python
from flask import Flask
from timetrace.integrations.flask import TimeTraceMiddleware
from timetrace.config import TraceConfig
from timetrace.plugins import enable_httpx

app = Flask(__name__)

# Configure timetrace
config = TraceConfig(
    mode="record",
    cassette_dir="./cassettes",
)

# Wrap WSGI app
app.wsgi_app = TimeTraceMiddleware(app.wsgi_app, config=config)

# Enable plugins
enable_httpx()

@app.route("/checkout", methods=["POST"])
def checkout():
    # Your code with httpx calls
    return {"status": "ok"}
```

### Option 2: init_app Helper

```python
from flask import Flask
from timetrace.integrations.flask import init_app
from timetrace.config import TraceConfig

app = Flask(__name__)

config = TraceConfig(mode="record", cassette_dir="./cassettes")
init_app(app, config)
```

## Environment Configuration

```bash
# Record mode
TIMETRACER_MODE=record python app.py

# Replay mode
TIMETRACER_MODE=replay TIMETRACER_CASSETTE=./cassettes/POST__checkout__a91c.json python app.py
```

## Features

All standard Timetrace features work with Flask:

- Request/response capture
- httpx/requests plugin support
- SQLAlchemy/Redis plugins
- Hybrid replay mode
- Cassette generation
- Terminal summaries

## Example Output

```
TIMETRACE [OK] recorded POST /checkout  id=b42f  status=200  total=312ms  deps=http.client:2
  cassette: cassettes/2026-01-15/POST__checkout__b42f.json
```
