# Hybrid Replay Example

This example demonstrates hybrid replay - mocking external APIs while keeping other dependencies live.

## Scenario

A checkout endpoint that:
1. Calls an external payment API (Stripe) - **mocked during replay**
2. Stores order in database - **kept live during replay**

## Setup

```bash
pip install fastapi uvicorn httpx
pip install -e ../../  # Install timetrace from source
```

## Files

- `app.py` - FastAPI application with hybrid replay configured
- `Run instructions below

## Running

### 1. Record Mode (captures the Stripe call)

```bash
TIMETRACER_MODE=record python app.py
```

Make a request:
```bash
curl -X POST http://localhost:8000/checkout \
  -H "Content-Type: application/json" \
  -d '{"amount": 1000, "currency": "usd"}'
```

### 2. Replay Mode (Stripe mocked, DB live)

```bash
TIMETRACER_MODE=replay \
TIMETRACER_CASSETTE=./cassettes/POST__checkout__*.json \
TIMETRACER_MOCK_PLUGINS=http \
python app.py
```

Now the Stripe API call is mocked from the recording, but any database operations would be live.
