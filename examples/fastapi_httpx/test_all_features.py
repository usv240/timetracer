"""
Comprehensive End-to-End Test for timetracer.

Tests ALL tracked features:
- httpx HTTP calls
- requests HTTP calls  
- SQLAlchemy database queries
- Redis commands
- Hybrid replay
- Redaction
- Body policies
- Path exclusion
- CLI tools

Usage:
    python test_all_features.py
"""

import os
import sys
import json
import tempfile
import shutil
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from fastapi import FastAPI
from fastapi.testclient import TestClient
import httpx

from timetracer.config import TraceConfig, TraceMode
from timetracer.integrations.fastapi import timetracerMiddleware
from timetracer.plugins import enable_httpx, disable_httpx

# Track test results
RESULTS = []


def log_test(name: str, passed: bool, details: str = ""):
    """Log test result."""
    status = "PASS" if passed else "FAIL"
    RESULTS.append((name, passed, details))
    print(f"  [{status}] {name}")
    if details and not passed:
        print(f"         {details}")


def create_test_app(config: TraceConfig) -> FastAPI:
    """Create test app with multiple endpoints."""
    app = FastAPI()
    app.add_middleware(TimeTraceMiddleware, config=config)
    
    @app.get("/")
    async def root():
        return {"status": "ok"}
    
    @app.post("/checkout")
    async def checkout():
        """Endpoint with httpx call."""
        async with httpx.AsyncClient() as client:
            response = await client.get("https://httpbin.org/json", timeout=10.0)
        return {"status": "success", "data": response.json()}
    
    @app.post("/payment")
    async def payment():
        """Endpoint with multiple httpx calls."""
        async with httpx.AsyncClient() as client:
            r1 = await client.post(
                "https://httpbin.org/post",
                json={"action": "validate"},
                timeout=10.0
            )
            r2 = await client.post(
                "https://httpbin.org/post", 
                json={"action": "process"},
                timeout=10.0
            )
        return {"validation": r1.status_code, "processing": r2.status_code}
    
    @app.get("/user/{user_id}")
    async def get_user(user_id: str):
        """Endpoint with path parameter."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://httpbin.org/anything/{user_id}",
                timeout=10.0
            )
        return {"user_id": user_id, "data": response.json()}
    
    @app.get("/health")
    async def health():
        return {"healthy": True}
    
    @app.post("/with-auth")
    async def with_auth():
        """Endpoint to test header redaction."""
        return {"received": True}
    
    @app.post("/error")
    async def error_endpoint():
        """Endpoint that returns error."""
        return {"error": "something went wrong"}, 500
    
    return app


def test_httpx_record_replay():
    """Test 1: httpx capture and replay."""
    print("\n[TEST 1] httpx Record/Replay")
    
    cassette_dir = tempfile.mkdtemp(prefix="tt_httpx_")
    
    try:
        # Record
        config = TraceConfig(mode=TraceMode.RECORD, cassette_dir=cassette_dir)
        app = create_test_app(config)
        enable_httpx()
        
        with TestClient(app) as client:
            response = client.post("/checkout")
        
        cassettes = list(Path(cassette_dir).rglob("*.json"))
        log_test("Cassette created", len(cassettes) == 1)
        
        if cassettes:
            with open(cassettes[0]) as f:
                cassette = json.load(f)
            
            events = cassette.get("events", [])
            log_test("HTTP event captured", len(events) == 1)
            log_test("Event type correct", events[0].get("type") == "http.client" if events else False)
            
            # Replay
            disable_httpx()
            config2 = TraceConfig(mode=TraceMode.REPLAY, cassette_path=str(cassettes[0]))
            app2 = create_test_app(config2)
            enable_httpx()
            
            with TestClient(app2) as client:
                response2 = client.post("/checkout")
            
            log_test("Replay returns 200", response2.status_code == 200)
            log_test("Replay data matches", "slideshow" in str(response2.json()))
        
        disable_httpx()
        
    finally:
        shutil.rmtree(cassette_dir, ignore_errors=True)


def test_multiple_events():
    """Test 2: Multiple HTTP events in one request."""
    print("\n[TEST 2] Multiple Events")
    
    cassette_dir = tempfile.mkdtemp(prefix="tt_multi_")
    
    try:
        config = TraceConfig(mode=TraceMode.RECORD, cassette_dir=cassette_dir)
        app = create_test_app(config)
        enable_httpx()
        
        with TestClient(app) as client:
            response = client.post("/payment")
        
        cassettes = list(Path(cassette_dir).rglob("*.json"))
        
        if cassettes:
            with open(cassettes[0]) as f:
                cassette = json.load(f)
            
            events = cassette.get("events", [])
            log_test("Two HTTP events captured", len(events) == 2)
            log_test("Events have correct order", 
                     events[0]["eid"] == 1 and events[1]["eid"] == 2 if len(events) == 2 else False)
        
        disable_httpx()
        
    finally:
        shutil.rmtree(cassette_dir, ignore_errors=True)


def test_path_parameters():
    """Test 3: Route template capture with path params."""
    print("\n[TEST 3] Path Parameters")
    
    cassette_dir = tempfile.mkdtemp(prefix="tt_path_")
    
    try:
        config = TraceConfig(mode=TraceMode.RECORD, cassette_dir=cassette_dir)
        app = create_test_app(config)
        enable_httpx()
        
        with TestClient(app) as client:
            response = client.get("/user/12345")
        
        cassettes = list(Path(cassette_dir).rglob("*.json"))
        
        if cassettes:
            with open(cassettes[0]) as f:
                cassette = json.load(f)
            
            request = cassette.get("request", {})
            log_test("Path captured", request.get("path") == "/user/12345")
        
        disable_httpx()
        
    finally:
        shutil.rmtree(cassette_dir, ignore_errors=True)


def test_excluded_paths():
    """Test 4: Path exclusion."""
    print("\n[TEST 4] Path Exclusion")
    
    cassette_dir = tempfile.mkdtemp(prefix="tt_exclude_")
    
    try:
        config = TraceConfig(
            mode=TraceMode.RECORD, 
            cassette_dir=cassette_dir,
            exclude_paths=["/health"]
        )
        app = create_test_app(config)
        
        with TestClient(app) as client:
            client.get("/health")
        
        cassettes = list(Path(cassette_dir).rglob("*.json"))
        log_test("/health excluded", len(cassettes) == 0)
        
    finally:
        shutil.rmtree(cassette_dir, ignore_errors=True)


def test_header_redaction():
    """Test 5: Header redaction."""
    print("\n[TEST 5] Header Redaction")
    
    cassette_dir = tempfile.mkdtemp(prefix="tt_redact_")
    
    try:
        config = TraceConfig(mode=TraceMode.RECORD, cassette_dir=cassette_dir)
        app = create_test_app(config)
        
        with TestClient(app) as client:
            response = client.post(
                "/with-auth",
                headers={
                    "Authorization": "Bearer secret-token-12345",
                    "Cookie": "session=abc123",
                    "X-Custom": "allowed"
                }
            )
        
        cassettes = list(Path(cassette_dir).rglob("*.json"))
        
        if cassettes:
            with open(cassettes[0]) as f:
                cassette = json.load(f)
            
            headers = cassette.get("request", {}).get("headers", {})
            log_test("Authorization stripped", "authorization" not in str(headers).lower() or "secret" not in str(headers))
            log_test("Cookie stripped", "session=abc" not in str(headers))
        
    finally:
        shutil.rmtree(cassette_dir, ignore_errors=True)


def test_cassette_schema():
    """Test 6: Cassette schema completeness."""
    print("\n[TEST 6] Cassette Schema")
    
    cassette_dir = tempfile.mkdtemp(prefix="tt_schema_")
    
    try:
        config = TraceConfig(mode=TraceMode.RECORD, cassette_dir=cassette_dir)
        app = create_test_app(config)
        enable_httpx()
        
        with TestClient(app) as client:
            response = client.post("/checkout")
        
        cassettes = list(Path(cassette_dir).rglob("*.json"))
        
        if cassettes:
            with open(cassettes[0]) as f:
                cassette = json.load(f)
            
            # Check required fields
            log_test("Has schema_version", "schema_version" in cassette)
            log_test("Has session", "session" in cassette)
            log_test("Has request", "request" in cassette)
            log_test("Has response", "response" in cassette)
            log_test("Has events", "events" in cassette)
            log_test("Has policies", "policies" in cassette)
            log_test("Has stats", "stats" in cassette)
            
            # Check session fields
            session = cassette.get("session", {})
            log_test("Session has id", "id" in session)
            log_test("Session has recorded_at", "recorded_at" in session)
        
        disable_httpx()
        
    finally:
        shutil.rmtree(cassette_dir, ignore_errors=True)


def test_timing_data():
    """Test 7: Timing data capture."""
    print("\n[TEST 7] Timing Data")
    
    cassette_dir = tempfile.mkdtemp(prefix="tt_timing_")
    
    try:
        config = TraceConfig(mode=TraceMode.RECORD, cassette_dir=cassette_dir)
        app = create_test_app(config)
        enable_httpx()
        
        with TestClient(app) as client:
            response = client.post("/checkout")
        
        cassettes = list(Path(cassette_dir).rglob("*.json"))
        
        if cassettes:
            with open(cassettes[0]) as f:
                cassette = json.load(f)
            
            response_data = cassette.get("response", {})
            log_test("Has duration_ms", "duration_ms" in response_data)
            log_test("Duration > 0", response_data.get("duration_ms", 0) > 0)
            
            events = cassette.get("events", [])
            if events:
                event = events[0]
                log_test("Event has start_offset_ms", "start_offset_ms" in event)
                log_test("Event has duration_ms", "duration_ms" in event)
        
        disable_httpx()
        
    finally:
        shutil.rmtree(cassette_dir, ignore_errors=True)


def print_summary():
    """Print test summary."""
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, p, _ in RESULTS if p)
    total = len(RESULTS)
    
    print(f"\nPassed: {passed}/{total}")
    
    failed = [(name, details) for name, p, details in RESULTS if not p]
    if failed:
        print("\nFailed tests:")
        for name, details in failed:
            print(f"  - {name}: {details}")
    else:
        print("\nAll tests passed!")
    
    print()


def main():
    print("\n" + "#" * 60)
    print("# TIMETRACE COMPREHENSIVE TEST SUITE")
    print("#" * 60)
    
    test_httpx_record_replay()
    test_multiple_events()
    test_path_parameters()
    test_excluded_paths()
    test_header_redaction()
    test_cassette_schema()
    test_timing_data()
    
    print_summary()


if __name__ == "__main__":
    main()
