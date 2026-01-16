"""
Hybrid Replay Example

Demonstrates using hybrid replay to mock external APIs 
while keeping other dependencies (like databases) live.
"""

import os
import httpx
from fastapi import FastAPI

from timetrace.config import TraceConfig
from timetrace.integrations.fastapi import TimeTraceMiddleware
from timetrace.plugins.httpx_plugin import enable_httpx

app = FastAPI(title="Hybrid Replay Example")

# Configure timetrace with hybrid replay support
config = TraceConfig(
    mode=os.environ.get("TIMETRACE_MODE", "off"),
    cassette_dir="./cassettes",
    cassette_path=os.environ.get("TIMETRACE_CASSETTE"),
    # For hybrid replay: only mock HTTP, keep DB live
    mock_plugins=os.environ.get("TIMETRACE_MOCK_PLUGINS", "").split(",") if os.environ.get("TIMETRACE_MOCK_PLUGINS") else [],
    live_plugins=os.environ.get("TIMETRACE_LIVE_PLUGINS", "").split(",") if os.environ.get("TIMETRACE_LIVE_PLUGINS") else [],
)

# Add middleware
app.add_middleware(TimeTraceMiddleware, config=config)

# Enable httpx capture
enable_httpx()


# Simulated external payment API
STRIPE_API = "https://api.stripe.com/v1"


@app.post("/checkout")
async def checkout(payload: dict):
    """
    Process a checkout.
    
    This endpoint:
    1. Calls Stripe API to create a charge (mocked in hybrid replay)
    2. Would store order in DB (kept live in hybrid replay)
    """
    amount = payload.get("amount", 0)
    currency = payload.get("currency", "usd")
    
    # External API call - will be mocked in replay mode
    async with httpx.AsyncClient() as client:
        # In real scenario, this would call Stripe
        # For demo, we call a mock endpoint
        response = await client.post(
            "https://httpbin.org/post",
            json={
                "amount": amount,
                "currency": currency,
                "source": "tok_visa",
            },
            headers={"Authorization": "Bearer sk_test_xxxx"},
        )
        external_result = response.json()
    
    # In real scenario, you'd store order in database here
    # This would be LIVE even during replay with mock_plugins=["http"]
    order = {
        "id": "order_123",
        "amount": amount,
        "currency": currency,
        "status": "completed",
        "payment_provider": "stripe",
    }
    
    return {
        "order": order,
        "payment_response": external_result.get("url", "captured"),
    }


@app.get("/health")
async def health():
    """Health check endpoint (excluded from tracing)."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
