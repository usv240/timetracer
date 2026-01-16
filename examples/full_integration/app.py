"""
Full Integration Example - FastAPI App

A realistic API that exercises ALL Timetrace features:
- Multiple HTTP methods (GET, POST, PUT, DELETE)
- External API calls (httpx)
- Database operations (SQLAlchemy + SQLite)
- Redis caching
- Error scenarios (4xx, 5xx)
- Large responses
- Different content types
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import PlainTextResponse, Response
from sqlalchemy import create_engine, text
import httpx
import json
import sys
from pathlib import Path

# Add timetrace to path if running locally
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from timetrace.config import TraceConfig
from timetrace.integrations.fastapi import TimeTraceMiddleware
from timetrace.plugins import enable_httpx

# Create app
app = FastAPI(title="Full Integration Example")

# Add Timetrace middleware (configured via environment variables)
config = TraceConfig.from_env()
app.add_middleware(TimeTraceMiddleware, config=config)

# Enable httpx plugin for tracking external HTTP calls
enable_httpx()

# Database setup (SQLite file)
DB_PATH = Path(__file__).parent / "example.db"
engine = create_engine(f"sqlite:///{DB_PATH}")

# Initialize database
def init_db():
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                price REAL NOT NULL
            )
        """))
        conn.execute(text("DELETE FROM products"))
        conn.execute(text("INSERT INTO products (name, price) VALUES ('Widget', 9.99)"))
        conn.execute(text("INSERT INTO products (name, price) VALUES ('Gadget', 19.99)"))
        conn.commit()

init_db()


# =============================================================================
# BASIC ENDPOINTS
# =============================================================================

@app.get("/")
def root():
    """Basic health check."""
    return {"status": "ok", "app": "full-integration-example"}


@app.get("/health")
def health():
    """Health endpoint (excluded from tracing)."""
    return {"healthy": True}


# =============================================================================
# HTTP METHODS
# =============================================================================

@app.get("/products")
def list_products():
    """List all products from database."""
    with engine.connect() as conn:
        result = conn.execute(text("SELECT id, name, price FROM products"))
        products = [{"id": r[0], "name": r[1], "price": r[2]} for r in result]
    return {"products": products}


@app.get("/products/{product_id}")
def get_product(product_id: int):
    """Get single product with path parameter."""
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT id, name, price FROM products WHERE id = :id"),
            {"id": product_id}
        )
        row = result.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return {"id": row[0], "name": row[1], "price": row[2]}


@app.post("/products")
def create_product(name: str = Query(...), price: float = Query(...)):
    """Create product with query parameters."""
    with engine.connect() as conn:
        result = conn.execute(
            text("INSERT INTO products (name, price) VALUES (:name, :price)"),
            {"name": name, "price": price}
        )
        conn.commit()
        product_id = result.lastrowid
    
    return {"id": product_id, "name": name, "price": price}


@app.delete("/products/{product_id}")
def delete_product(product_id: int):
    """Delete product."""
    with engine.connect() as conn:
        conn.execute(
            text("DELETE FROM products WHERE id = :id"),
            {"id": product_id}
        )
        conn.commit()
    return {"deleted": True}


# =============================================================================
# EXTERNAL API CALLS
# =============================================================================

@app.get("/external/json")
async def fetch_external_json():
    """Fetch JSON from external API."""
    async with httpx.AsyncClient() as client:
        response = await client.get("https://httpbin.org/json", timeout=10.0)
    return {"external_data": response.json()}


@app.get("/external/text")
async def fetch_external_text():
    """Fetch plain text from external API."""
    async with httpx.AsyncClient() as client:
        response = await client.get("https://httpbin.org/robots.txt", timeout=10.0)
    return PlainTextResponse(response.text)


@app.post("/external/echo")
async def echo_to_external(data: dict):
    """Post data to external API and get echo."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://httpbin.org/post",
            json=data,
            timeout=10.0
        )
    return {"echoed": response.json().get("json", {})}


@app.get("/external/multiple")
async def multiple_external_calls():
    """Make multiple external calls in one request."""
    async with httpx.AsyncClient() as client:
        r1 = await client.get("https://httpbin.org/get", timeout=10.0)
        r2 = await client.get("https://httpbin.org/headers", timeout=10.0)
        r3 = await client.get("https://httpbin.org/ip", timeout=10.0)
    
    return {
        "calls": 3,
        "ip": r3.json().get("origin", "unknown"),
    }


# =============================================================================
# ERROR SCENARIOS
# =============================================================================

@app.get("/error/404")
def error_not_found():
    """Return 404 error."""
    raise HTTPException(status_code=404, detail="Resource not found")


@app.get("/error/500")
def error_internal():
    """Return 500 error."""
    raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/error/422")
def error_validation():
    """Return 422 validation error."""
    raise HTTPException(status_code=422, detail="Validation failed")


@app.get("/external/error")
async def external_error():
    """Call external API that returns error."""
    async with httpx.AsyncClient() as client:
        response = await client.get("https://httpbin.org/status/500", timeout=10.0)
    return {"external_status": response.status_code}


# =============================================================================
# EDGE CASES
# =============================================================================

@app.get("/edge/large-response")
def large_response(size: int = Query(default=100000)):
    """Return large response body."""
    data = "x" * min(size, 500000)  # Cap at 500KB
    return {"size": len(data), "data": data}


@app.get("/edge/empty")
def empty_response():
    """Return empty response."""
    return Response(status_code=204)


@app.get("/edge/binary")
def binary_response():
    """Return binary data."""
    data = bytes(range(256))
    return Response(content=data, media_type="application/octet-stream")


@app.get("/edge/slow")
async def slow_response():
    """Simulate slow response."""
    import asyncio
    await asyncio.sleep(0.5)  # 500ms delay
    return {"delayed": True}


@app.get("/edge/query-params")
def with_query_params(
    name: str = Query(default="test"),
    count: int = Query(default=1),
    active: bool = Query(default=True),
):
    """Endpoint with multiple query parameters."""
    return {"name": name, "count": count, "active": active}


@app.post("/edge/large-request")
async def large_request(data: dict):
    """Accept large request body."""
    return {"received_keys": list(data.keys()), "size": len(str(data))}


# =============================================================================
# SENSITIVE DATA (for redaction testing)
# =============================================================================

@app.post("/auth/login")
def login(username: str = Query(...), password: str = Query(...)):
    """Login endpoint with sensitive data."""
    # Password should be redacted in cassette
    if username == "admin" and password == "secret":
        return {"token": "fake-jwt-token-12345", "user": username}
    raise HTTPException(status_code=401, detail="Invalid credentials")


@app.get("/auth/me")
def get_me():
    """Protected endpoint (tests Authorization header redaction)."""
    return {"user": "test-user"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
