"""
Example FastAPI app for pytest fixture testing.
"""

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from timetracer.config import TraceConfig
from timetracer.integrations.fastapi import TimeTracerMiddleware
from timetracer.plugins import enable_httpx

app = FastAPI(title="pytest Example App")

# Add middleware
config = TraceConfig.from_env()
app.add_middleware(TimeTracerMiddleware, config=config)

# Enable httpx plugin
enable_httpx()


@app.get("/")
def root():
    """Health check."""
    return {"status": "ok"}


@app.get("/fetch-data")
def fetch_data():
    """Fetch data from external API."""
    with httpx.Client() as client:
        response = client.get("https://httpbin.org/json")
        data = response.json()
    return {"status": "success", "data": data}


@app.get("/user/{user_id}")
def get_user(user_id: int):
    """Get user by ID."""
    with httpx.Client() as client:
        response = client.get(f"https://httpbin.org/anything/user/{user_id}")
        data = response.json()
    return {"user_id": user_id, "data": data}


# Test client for use in tests
client = TestClient(app)
