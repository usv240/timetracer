# FastAPI + aiohttp Example

This example demonstrates using Timetracer with FastAPI and aiohttp.

## Setup

```bash
pip install timetracer[fastapi,aiohttp]
```

## Run in Record Mode

```bash
TIMETRACER_MODE=record uvicorn app:app --reload
```

Then make some requests:
```bash
curl http://localhost:8000/
curl http://localhost:8000/fetch-data
curl -X POST http://localhost:8000/submit
```

Cassettes are saved to `./cassettes/`.

## Run in Replay Mode

```bash
TIMETRACER_MODE=replay \
  TIMETRACER_CASSETTE=./cassettes/<your-cassette>.json \
  uvicorn app:app
```

## Run Tests

```bash
pytest test_app.py -v
```
