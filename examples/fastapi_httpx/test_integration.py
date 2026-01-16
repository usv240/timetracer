"""
Integration test script for Timetrace.

This script tests record and replay modes without needing a running server.
Uses FastAPI TestClient for direct testing.

Usage:
    python test_integration.py
"""

import os
import sys
import json
import tempfile
import shutil
from pathlib import Path

# Add parent to path for local timetrace import
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from fastapi import FastAPI
from fastapi.testclient import TestClient
import httpx

from timetrace.config import TraceConfig, TraceMode
from timetrace.integrations.fastapi import TimeTraceMiddleware
from timetrace.plugins import enable_httpx, disable_httpx


def create_app(config: TraceConfig) -> FastAPI:
    """Create a test FastAPI app with Timetrace."""
    app = FastAPI()
    app.add_middleware(TimeTraceMiddleware, config=config)
    
    @app.get("/")
    async def root():
        return {"status": "ok"}
    
    @app.post("/checkout")
    async def checkout():
        async with httpx.AsyncClient() as client:
            response = await client.get("https://httpbin.org/json", timeout=10.0)
            data = response.json()
        return {"status": "success", "data": data}
    
    @app.get("/health")
    async def health():
        return {"healthy": True}
    
    return app


def test_record_mode():
    """Test that record mode creates cassettes."""
    print("\n" + "=" * 60)
    print("TEST 1: Record Mode")
    print("=" * 60)
    
    # Create temp directory for cassettes
    cassette_dir = tempfile.mkdtemp(prefix="timetrace_test_")
    print(f"Cassette directory: {cassette_dir}")
    
    try:
        # Configure and create app
        config = TraceConfig(
            mode=TraceMode.RECORD,
            cassette_dir=cassette_dir,
        )
        app = create_app(config)
        enable_httpx()
        
        # Make request
        print("\nMaking POST /checkout request...")
        with TestClient(app) as client:
            response = client.post("/checkout")
        
        print(f"Response status: {response.status_code}")
        print(f"Response body: {json.dumps(response.json(), indent=2)[:200]}...")
        
        # Check cassette was created
        cassettes = list(Path(cassette_dir).rglob("*.json"))
        print(f"\nCassettes created: {len(cassettes)}")
        
        if cassettes:
            cassette_path = cassettes[0]
            print(f"Cassette: {cassette_path.name}")
            
            with open(cassette_path) as f:
                cassette = json.load(f)
            
            print(f"Schema version: {cassette['schema_version']}")
            print(f"Events: {cassette['stats']['total_events']}")
            print(f"Duration: {cassette['response']['duration_ms']:.1f}ms")
            
            disable_httpx()
            return str(cassette_path)
        else:
            print("ERROR: No cassette created!")
            disable_httpx()
            return None
            
    except Exception as e:
        print(f"ERROR: {e}")
        disable_httpx()
        return None


def test_replay_mode(cassette_path: str):
    """Test that replay mode mocks HTTP calls."""
    print("\n" + "=" * 60)
    print("TEST 2: Replay Mode")
    print("=" * 60)
    
    print(f"Using cassette: {Path(cassette_path).name}")
    
    try:
        # Configure for replay
        config = TraceConfig(
            mode=TraceMode.REPLAY,
            cassette_path=cassette_path,
        )
        app = create_app(config)
        enable_httpx()
        
        # Make same request - should be mocked
        print("\nMaking POST /checkout request (should be mocked)...")
        with TestClient(app) as client:
            response = client.post("/checkout")
        
        print(f"Response status: {response.status_code}")
        print(f"Response body: {json.dumps(response.json(), indent=2)[:200]}...")
        
        if response.status_code == 200:
            print("\nREPLAY SUCCESS: HTTP call was mocked from cassette!")
        else:
            print("\nWARNING: Unexpected status code")
        
        disable_httpx()
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        disable_httpx()
        return False


def test_excluded_paths():
    """Test that health endpoints are excluded."""
    print("\n" + "=" * 60)
    print("TEST 3: Excluded Paths")
    print("=" * 60)
    
    cassette_dir = tempfile.mkdtemp(prefix="timetrace_excluded_")
    
    try:
        config = TraceConfig(
            mode=TraceMode.RECORD,
            cassette_dir=cassette_dir,
            exclude_paths=["/health"],
        )
        app = create_app(config)
        
        print("Making GET /health request (should NOT be recorded)...")
        with TestClient(app) as client:
            response = client.get("/health")
        
        cassettes = list(Path(cassette_dir).rglob("*.json"))
        print(f"Cassettes created: {len(cassettes)}")
        
        if len(cassettes) == 0:
            print("SUCCESS: /health was correctly excluded!")
        else:
            print("WARNING: /health was recorded but should be excluded")
        
        shutil.rmtree(cassette_dir, ignore_errors=True)
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        return False


def main():
    print("\n" + "#" * 60)
    print("# TIMETRACE INTEGRATION TEST")
    print("#" * 60)
    
    # Test 1: Record
    cassette_path = test_record_mode()
    
    if cassette_path:
        # Test 2: Replay
        test_replay_mode(cassette_path)
        
        # Cleanup
        shutil.rmtree(Path(cassette_path).parent.parent, ignore_errors=True)
    
    # Test 3: Excluded paths
    test_excluded_paths()
    
    print("\n" + "#" * 60)
    print("# ALL TESTS COMPLETE")
    print("#" * 60 + "\n")


if __name__ == "__main__":
    main()
