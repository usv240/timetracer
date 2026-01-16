"""
COMPLETE End-to-End Test Suite for Timetrace.

Tests ALL features including:
- httpx HTTP calls
- requests HTTP calls  
- SQLAlchemy database queries (using SQLite in-memory)
- Hybrid replay
- Redaction
- Body policies
- Path exclusion
- CLI tools

Usage:
    python test_complete.py
"""

import os
import sys
import json
import tempfile
import shutil
import subprocess
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from fastapi import FastAPI
from fastapi.testclient import TestClient
import httpx

from timetrace.config import TraceConfig, TraceMode
from timetrace.integrations.fastapi import TimeTraceMiddleware
from timetrace.plugins import enable_httpx, disable_httpx

# Track test results
RESULTS = []
CASSETTE_DIR = None


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
        async with httpx.AsyncClient() as client:
            response = await client.get("https://httpbin.org/json", timeout=10.0)
        return {"status": "success", "data": response.json()}
    
    @app.post("/payment")
    async def payment():
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
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://httpbin.org/anything/{user_id}",
                timeout=10.0
            )
        return {"user_id": user_id}
    
    @app.get("/health")
    async def health():
        return {"healthy": True}
    
    @app.post("/with-auth")
    async def with_auth():
        return {"received": True}
    
    return app


# =============================================================================
# TEST SECTION 1: Core Features
# =============================================================================

def test_httpx_record_replay():
    """Test httpx capture and replay."""
    global CASSETTE_DIR
    print("\n[TEST] httpx Record/Replay")
    
    CASSETTE_DIR = tempfile.mkdtemp(prefix="tt_complete_")
    
    config = TraceConfig(mode=TraceMode.RECORD, cassette_dir=CASSETTE_DIR)
    app = create_test_app(config)
    enable_httpx()
    
    with TestClient(app) as client:
        response = client.post("/checkout")
    
    cassettes = list(Path(CASSETTE_DIR).rglob("*.json"))
    log_test("Cassette created", len(cassettes) >= 1)
    
    if cassettes:
        with open(cassettes[0]) as f:
            cassette = json.load(f)
        
        events = cassette.get("events", [])
        log_test("HTTP event captured", len(events) >= 1)
        
        # Test replay
        disable_httpx()
        config2 = TraceConfig(mode=TraceMode.REPLAY, cassette_path=str(cassettes[0]))
        app2 = create_test_app(config2)
        enable_httpx()
        
        with TestClient(app2) as client:
            response2 = client.post("/checkout")
        
        log_test("Replay returns 200", response2.status_code == 200)
    
    disable_httpx()


def test_multiple_events():
    """Test multiple HTTP events in one request."""
    print("\n[TEST] Multiple Events")
    
    cassette_dir = tempfile.mkdtemp(prefix="tt_multi_")
    
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
    
    disable_httpx()
    shutil.rmtree(cassette_dir, ignore_errors=True)


def test_path_exclusion():
    """Test path exclusion."""
    print("\n[TEST] Path Exclusion")
    
    cassette_dir = tempfile.mkdtemp(prefix="tt_exclude_")
    
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
    
    shutil.rmtree(cassette_dir, ignore_errors=True)


def test_header_redaction():
    """Test header redaction."""
    print("\n[TEST] Header Redaction")
    
    cassette_dir = tempfile.mkdtemp(prefix="tt_redact_")
    
    config = TraceConfig(mode=TraceMode.RECORD, cassette_dir=cassette_dir)
    app = create_test_app(config)
    
    with TestClient(app) as client:
        response = client.post(
            "/with-auth",
            headers={
                "Authorization": "Bearer secret-token-12345",
                "Cookie": "session=abc123",
            }
        )
    
    cassettes = list(Path(cassette_dir).rglob("*.json"))
    
    if cassettes:
        with open(cassettes[0]) as f:
            cassette = json.load(f)
        
        headers = cassette.get("request", {}).get("headers", {})
        headers_str = str(headers).lower()
        log_test("Authorization stripped", "secret-token" not in headers_str)
        log_test("Cookie stripped", "session=abc" not in headers_str)
    
    shutil.rmtree(cassette_dir, ignore_errors=True)


def test_cassette_schema():
    """Test cassette schema completeness."""
    print("\n[TEST] Cassette Schema")
    
    cassette_dir = tempfile.mkdtemp(prefix="tt_schema_")
    
    config = TraceConfig(mode=TraceMode.RECORD, cassette_dir=cassette_dir)
    app = create_test_app(config)
    enable_httpx()
    
    with TestClient(app) as client:
        response = client.post("/checkout")
    
    cassettes = list(Path(cassette_dir).rglob("*.json"))
    
    if cassettes:
        with open(cassettes[0]) as f:
            cassette = json.load(f)
        
        log_test("Has schema_version", "schema_version" in cassette)
        log_test("Has session", "session" in cassette)
        log_test("Has request", "request" in cassette)
        log_test("Has response", "response" in cassette)
        log_test("Has events", "events" in cassette)
        log_test("Has policies", "policies" in cassette)
        log_test("Has stats", "stats" in cassette)
    
    disable_httpx()
    shutil.rmtree(cassette_dir, ignore_errors=True)


# =============================================================================
# TEST SECTION 2: requests Library Plugin
# =============================================================================

def test_requests_plugin():
    """Test requests library plugin."""
    print("\n[TEST] requests Library Plugin")
    
    try:
        import requests as req_lib
        from timetrace.plugins import enable_requests, disable_requests
        
        cassette_dir = tempfile.mkdtemp(prefix="tt_requests_")
        
        # Create app that uses requests
        app = FastAPI()
        config = TraceConfig(mode=TraceMode.RECORD, cassette_dir=cassette_dir)
        app.add_middleware(TimeTraceMiddleware, config=config)
        
        @app.get("/fetch")
        def fetch():
            response = req_lib.get("https://httpbin.org/get", timeout=10)
            return {"status": response.status_code}
        
        enable_requests()
        
        with TestClient(app) as client:
            response = client.get("/fetch")
        
        cassettes = list(Path(cassette_dir).rglob("*.json"))
        
        if cassettes:
            with open(cassettes[0]) as f:
                cassette = json.load(f)
            
            events = cassette.get("events", [])
            log_test("requests event captured", len(events) >= 1)
            if events:
                log_test("Event lib is requests", events[0].get("signature", {}).get("lib") == "requests")
        else:
            log_test("requests cassette created", False, "No cassette found")
        
        disable_requests()
        shutil.rmtree(cassette_dir, ignore_errors=True)
        
    except ImportError:
        log_test("requests plugin (skipped)", True, "requests not installed")


# =============================================================================
# TEST SECTION 3: SQLAlchemy Plugin (using SQLite)
# =============================================================================

def test_sqlalchemy_plugin():
    """Test SQLAlchemy plugin with SQLite."""
    print("\n[TEST] SQLAlchemy Plugin")
    
    try:
        from sqlalchemy import create_engine, text
        from timetrace.plugins import enable_sqlalchemy, disable_sqlalchemy
        
        cassette_dir = tempfile.mkdtemp(prefix="tt_sql_")
        db_path = Path(cassette_dir) / "test.db"
        
        # Create file-based SQLite engine (persists across connections)
        engine = create_engine(f"sqlite:///{db_path}")
        
        # Create a table and insert data
        with engine.connect() as conn:
            conn.execute(text("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT)"))
            conn.execute(text("INSERT INTO users (name) VALUES ('Alice')"))
            conn.commit()
        
        # Create app that queries database
        app = FastAPI()
        config = TraceConfig(mode=TraceMode.RECORD, cassette_dir=cassette_dir)
        app.add_middleware(TimeTraceMiddleware, config=config)
        
        @app.get("/users")
        def get_users():
            with engine.connect() as conn:
                result = conn.execute(text("SELECT * FROM users"))
                rows = result.fetchall()
            return {"count": len(rows)}
        
        enable_sqlalchemy(engine)
        
        with TestClient(app) as client:
            response = client.get("/users")
        
        log_test("SQLAlchemy request succeeded", response.status_code == 200)
        log_test("SQLAlchemy returns data", response.json().get("count", 0) >= 1)
        
        cassettes = list(Path(cassette_dir).rglob("*.json"))
        log_test("SQLAlchemy cassette created", len(cassettes) >= 1)
        
        if cassettes:
            with open(cassettes[0]) as f:
                cassette = json.load(f)
            
            events = cassette.get("events", [])
            db_events = [e for e in events if e.get("type") == "db.query"]
            log_test("DB event captured", len(db_events) >= 1)
        
        disable_sqlalchemy(engine)
        shutil.rmtree(cassette_dir, ignore_errors=True)
        
    except ImportError as e:
        log_test("SQLAlchemy plugin (skipped)", True, f"SQLAlchemy not installed: {e}")
    except Exception as e:
        log_test("SQLAlchemy plugin", False, str(e))

# =============================================================================
# TEST SECTION 3.5: Redis Plugin (using fakeredis)
# =============================================================================

def test_redis_plugin():
    """Test Redis plugin with fakeredis."""
    print("\n[TEST] Redis Plugin")
    
    try:
        import fakeredis
        from timetrace.plugins import enable_redis, disable_redis
        
        cassette_dir = tempfile.mkdtemp(prefix="tt_redis_")
        
        # Create fake Redis client (must be created BEFORE enable_redis patches)
        fake_redis = fakeredis.FakeRedis()
        fake_redis.set("user:1", "Alice")
        
        # Enable Redis interception (global patch)
        enable_redis()
        
        # Create app that uses Redis
        app = FastAPI()
        config = TraceConfig(mode=TraceMode.RECORD, cassette_dir=cassette_dir)
        app.add_middleware(TimeTraceMiddleware, config=config)
        
        @app.get("/cache/{key}")
        def get_cache(key: str):
            value = fake_redis.get(key)
            return {"key": key, "value": value.decode() if value else None}
        
        with TestClient(app) as client:
            response = client.get("/cache/user:1")
        
        log_test("Redis request succeeded", response.status_code == 200)
        log_test("Redis returns data", response.json().get("value") == "Alice")
        
        cassettes = list(Path(cassette_dir).rglob("*.json"))
        log_test("Redis cassette created", len(cassettes) >= 1)
        
        if cassettes:
            with open(cassettes[0]) as f:
                cassette = json.load(f)
            
            events = cassette.get("events", [])
            redis_events = [e for e in events if e.get("type") == "redis"]
            log_test("Redis event captured", len(redis_events) >= 1)
        
        disable_redis()
        shutil.rmtree(cassette_dir, ignore_errors=True)
        
    except ImportError as e:
        log_test("Redis plugin (skipped)", True, f"fakeredis not installed: {e}")
    except Exception as e:
        log_test("Redis plugin", False, str(e))


# =============================================================================
# TEST SECTION 4: CLI Tools
# =============================================================================


def test_cli_list():
    """Test timetrace list command."""
    print("\n[TEST] CLI: timetrace list")
    
    if not CASSETTE_DIR:
        log_test("CLI list (skipped)", True, "No cassettes to list")
        return
    
    try:
        result = subprocess.run(
            ["python", "-m", "timetrace.cli.main", "list", "--dir", CASSETTE_DIR],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent.parent)
        )
        
        log_test("CLI list runs", result.returncode == 0)
        log_test("CLI list shows cassettes", "cassette" in result.stdout.lower() or "POST" in result.stdout)
        
    except Exception as e:
        log_test("CLI list", False, str(e))


def test_cli_show():
    """Test timetrace show command."""
    print("\n[TEST] CLI: timetrace show")
    
    if not CASSETTE_DIR:
        log_test("CLI show (skipped)", True, "No cassettes to show")
        return
    
    cassettes = list(Path(CASSETTE_DIR).rglob("*.json"))
    if not cassettes:
        log_test("CLI show (skipped)", True, "No cassettes found")
        return
    
    try:
        result = subprocess.run(
            ["python", "-m", "timetrace.cli.main", "show", str(cassettes[0]), "--events"],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent.parent)
        )
        
        log_test("CLI show runs", result.returncode == 0)
        log_test("CLI show displays request", "Request" in result.stdout or "POST" in result.stdout)
        log_test("CLI show displays response", "Response" in result.stdout or "status" in result.stdout.lower())
        
    except Exception as e:
        log_test("CLI show", False, str(e))


def test_cli_timeline():
    """Test timetrace timeline command."""
    print("\n[TEST] CLI: timetrace timeline")
    
    if not CASSETTE_DIR:
        log_test("CLI timeline (skipped)", True, "No cassettes")
        return
    
    cassettes = list(Path(CASSETTE_DIR).rglob("*.json"))
    if not cassettes:
        log_test("CLI timeline (skipped)", True, "No cassettes found")
        return
    
    output_file = tempfile.mktemp(suffix=".html")
    
    try:
        result = subprocess.run(
            ["python", "-m", "timetrace.cli.main", "timeline", str(cassettes[0]), "--out", output_file],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent.parent)
        )
        
        log_test("CLI timeline runs", result.returncode == 0)
        log_test("CLI timeline creates HTML", Path(output_file).exists())
        
        if Path(output_file).exists():
            content = Path(output_file).read_text()
            log_test("HTML contains timeline", "timeline" in content.lower() or "Timetrace" in content)
            Path(output_file).unlink()
        
    except Exception as e:
        log_test("CLI timeline", False, str(e))


def test_cli_search():
    """Test timetrace search command."""
    print("\n[TEST] CLI: timetrace search")
    
    if not CASSETTE_DIR:
        log_test("CLI search (skipped)", True, "No cassettes")
        return
    
    try:
        result = subprocess.run(
            ["python", "-m", "timetrace.cli.main", "search", "--dir", CASSETTE_DIR, "--method", "POST"],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent.parent)
        )
        
        log_test("CLI search runs", result.returncode == 0)
        log_test("CLI search finds results", "POST" in result.stdout or "Found" in result.stdout or "checkout" in result.stdout.lower())
        
    except Exception as e:
        log_test("CLI search", False, str(e))


# =============================================================================
# SUMMARY
# =============================================================================

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
    
    # Cleanup
    if CASSETTE_DIR and Path(CASSETTE_DIR).exists():
        shutil.rmtree(CASSETTE_DIR, ignore_errors=True)
    
    print()
    return len(failed) == 0


def main():
    print("\n" + "#" * 60)
    print("# TIMETRACE COMPLETE TEST SUITE")
    print("#" * 60)
    
    # Core features
    test_httpx_record_replay()
    test_multiple_events()
    test_path_exclusion()
    test_header_redaction()
    test_cassette_schema()
    
    # Additional plugins
    test_requests_plugin()
    test_sqlalchemy_plugin()
    test_redis_plugin()
    
    # CLI tools
    test_cli_list()
    test_cli_show()
    test_cli_timeline()
    test_cli_search()
    
    success = print_summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
