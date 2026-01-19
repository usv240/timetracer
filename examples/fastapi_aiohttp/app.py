"""
Example FastAPI app demonstrating Timetracer with aiohttp.

This app shows how to:
1. Set up TimeTracerMiddleware
2. Enable aiohttp plugin
3. Record outbound HTTP calls made with aiohttp
4. Replay cassettes for testing

Run in record mode:
    TIMETRACER_MODE=record uvicorn app:app --reload

Run in replay mode:
    TIMETRACER_MODE=replay TIMETRACER_CASSETTE=./cassettes/<file>.json uvicorn app:app
"""

import aiohttp
from fastapi import FastAPI

from timetracer.config import TraceConfig
from timetracer.integrations.fastapi import TimeTracerMiddleware
from timetracer.plugins import enable_aiohttp

# Create FastAPI app
app = FastAPI(
    title="Timetracer aiohttp Example",
    description="Demo app showing aiohttp integration",
)

# Configure Timetracer
config = TraceConfig.from_env()

# Add middleware
app.add_middleware(TimeTracerMiddleware, config=config)

# Enable aiohttp plugin for outbound call capture
enable_aiohttp()


@app.get("/")
async def root():
    """Simple health check."""
    return {"status": "ok", "client": "aiohttp"}


@app.get("/fetch-data")
async def fetch_data():
    """
    Fetch data from external API using aiohttp.
    
    In record mode: The aiohttp call is captured.
    In replay mode: The call is mocked using the recorded response.
    """
    async with aiohttp.ClientSession() as session:
        async with session.get("https://httpbin.org/json") as resp:
            data = await resp.json()

    return {
        "status": "success",
        "data": data,
    }


@app.get("/user/{user_id}")
async def get_user(user_id: str):
    """
    Fetch user data with path parameter.
    
    Shows how route templates work with aiohttp.
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://httpbin.org/anything/user/{user_id}") as resp:
            data = await resp.json()

    return {
        "user_id": user_id,
        "data": data,
    }


@app.post("/submit")
async def submit_data():
    """
    Submit data to external API using aiohttp POST.
    
    Demonstrates request body capture.
    """
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://httpbin.org/post",
            json={"action": "submit", "value": 42},
        ) as resp:
            data = await resp.json()

    return {
        "status": "submitted",
        "response": data,
    }


@app.post("/multi-call")
async def multi_call():
    """
    Make multiple external calls.
    
    Shows how multiple dependency events are captured in one cassette.
    """
    async with aiohttp.ClientSession() as session:
        # Call 1: Get data
        async with session.get("https://httpbin.org/get") as resp1:
            get_data = await resp1.json()

        # Call 2: Post data
        async with session.post(
            "https://httpbin.org/post",
            json={"from_get": get_data.get("origin")},
        ) as resp2:
            post_data = await resp2.json()

    return {
        "get_result": get_data,
        "post_result": post_data,
    }


@app.get("/with-headers")
async def with_headers():
    """
    Make request with custom headers.
    
    Shows header capture and redaction.
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(
            "https://httpbin.org/headers",
            headers={
                "X-Custom-Header": "test-value",
                "X-Request-Id": "req-123",
            },
        ) as resp:
            data = await resp.json()

    return {"headers_echo": data}


@app.get("/with-params")
async def with_params():
    """
    Make request with query parameters.
    
    Shows query param capture.
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(
            "https://httpbin.org/get",
            params={"page": 1, "limit": 10, "filter": "active"},
        ) as resp:
            data = await resp.json()

    return {"result": data}
