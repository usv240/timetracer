"""
Example FastAPI app demonstrating Timetrace.

This app shows how to:
1. Set up TimeTraceMiddleware
2. Enable httpx plugin
3. Record outbound HTTP calls
4. Replay cassettes for testing

Run in record mode:
    TIMETRACE_MODE=record uvicorn app:app --reload

Run in replay mode:
    TIMETRACE_MODE=replay TIMETRACE_CASSETTE=./cassettes/<file>.json uvicorn app:app
"""

from fastapi import FastAPI
import httpx

from timetrace.config import TraceConfig
from timetrace.integrations.fastapi import TimeTraceMiddleware
from timetrace.plugins import enable_httpx

# Create FastAPI app
app = FastAPI(
    title="Timetrace Example",
    description="Demo app for time-travel debugging",
)

# Configure Timetrace
# In production, use TraceConfig.from_env() to load from environment
config = TraceConfig.from_env()

# Add middleware
app.add_middleware(TimeTraceMiddleware, config=config)

# Enable httpx plugin for outbound call capture
enable_httpx()


@app.get("/")
async def root():
    """Simple health check."""
    return {"status": "ok", "app": "timetrace-example"}


@app.post("/checkout")
async def checkout():
    """
    Example endpoint that makes an external API call.
    
    In record mode: The httpx call to httpbin.org is captured.
    In replay mode: The call is mocked using the recorded response.
    """
    async with httpx.AsyncClient() as client:
        # This call will be recorded/replayed by Timetrace
        response = await client.get(
            "https://httpbin.org/json",
            timeout=10.0,
        )
        external_data = response.json()
    
    return {
        "status": "checkout_complete",
        "external_data": external_data,
    }


@app.get("/user/{user_id}")
async def get_user(user_id: str):
    """
    Example endpoint with path parameter.
    
    Demonstrates route template capture.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://httpbin.org/anything/user/{user_id}",
            timeout=10.0,
        )
        data = response.json()
    
    return {
        "user_id": user_id,
        "data": data,
    }


@app.post("/payment")
async def process_payment():
    """
    Example endpoint that makes multiple external calls.
    
    Shows how multiple dependency events are captured.
    """
    async with httpx.AsyncClient() as client:
        # Call 1: Validate payment
        validate_response = await client.post(
            "https://httpbin.org/post",
            json={"action": "validate", "amount": 99.99},
            timeout=10.0,
        )
        
        # Call 2: Process payment
        process_response = await client.post(
            "https://httpbin.org/post",
            json={"action": "process", "validated": True},
            timeout=10.0,
        )
    
    return {
        "status": "payment_processed",
        "validation": validate_response.json(),
        "processing": process_response.json(),
    }


# Excluded endpoints (won't be recorded)
@app.get("/health")
async def health():
    """Health check - excluded from recording by default."""
    return {"healthy": True}


@app.get("/metrics")
async def metrics():
    """Metrics endpoint - excluded from recording by default."""
    return {"requests": 0}
