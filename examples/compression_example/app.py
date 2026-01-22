"""
Example FastAPI app demonstrating cassette compression.

Run with:
    TIMETRACER_MODE=record TIMETRACER_COMPRESSION=gzip python app.py

Or:
    TIMETRACER_MODE=record python app.py  # No compression (default)
"""

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from timetracer import CompressionType, TraceConfig
from timetracer.integrations.fastapi import TimeTracerMiddleware
from timetracer.plugins import enable_httpx

# Create app
app = FastAPI(title="Compression Example")

# Configure Timetracer with compression
# You can also use TIMETRACER_COMPRESSION=gzip env var
config = TraceConfig.from_env()

# Add middleware
app.add_middleware(TimeTracerMiddleware, config=config)

# Enable httpx plugin
enable_httpx()


@app.get("/")
async def root():
    """Simple endpoint."""
    return {"message": "Hello, World!"}


@app.get("/external")
async def fetch_external():
    """Endpoint that makes an external API call."""
    async with httpx.AsyncClient() as client:
        response = await client.get("https://httpbin.org/json")
        return response.json()


@app.get("/large-response")
async def large_response():
    """
    Endpoint that returns a large JSON response.
    This demonstrates the compression benefit.
    """
    # Generate a large response (good for testing compression)
    items = [
        {
            "id": i,
            "name": f"Item {i}",
            "description": f"This is a detailed description for item {i}. " * 5,
            "metadata": {
                "created_at": "2026-01-22T12:00:00Z",
                "updated_at": "2026-01-22T12:00:00Z",
                "tags": ["tag1", "tag2", "tag3"],
            },
        }
        for i in range(100)
    ]
    return {"items": items, "count": len(items)}


def demo_compression():
    """Run a demo showing compression in action."""
    import os
    from pathlib import Path

    print("=" * 60)
    print("Timetracer Compression Demo")
    print("=" * 60)
    print(f"\nCurrent mode: {config.mode.value}")
    print(f"Compression: {config.compression.value}")
    print(f"Cassette dir: {config.cassette_dir}")
    print()

    # Create test client
    client = TestClient(app)

    # Make some requests
    print("Making requests...")

    response = client.get("/")
    print(f"  GET / -> {response.status_code}")

    response = client.get("/large-response")
    print(f"  GET /large-response -> {response.status_code}")

    print()

    # Show cassette files if in record mode
    if config.mode.value == "record":
        cassette_dir = Path(config.cassette_dir)
        if cassette_dir.exists():
            cassettes = list(cassette_dir.rglob("*.json")) + list(
                cassette_dir.rglob("*.json.gz")
            )
            if cassettes:
                print("Created cassettes:")
                for cassette in cassettes:
                    size = cassette.stat().st_size
                    ext = ".gz" if cassette.suffix == ".gz" else ""
                    print(f"  {cassette.name}: {size:,} bytes")

    print("\nDone!")


if __name__ == "__main__":
    demo_compression()
