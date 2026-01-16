"""Pytest configuration for Timetrace tests."""

import pytest


@pytest.fixture
def sample_cassette_data():
    """Sample cassette data for testing."""
    return {
        "schema_version": "0.1",
        "session": {
            "id": "test-session-123",
            "recorded_at": "2026-01-15T00:00:00Z",
            "service": "test-service",
            "env": "test",
            "framework": "fastapi",
            "timetrace_version": "0.1.0",
            "python_version": "3.11.0",
        },
        "request": {
            "method": "POST",
            "path": "/checkout",
            "route_template": "/checkout",
            "headers": {"content-type": "application/json"},
            "query": {},
        },
        "response": {
            "status": 200,
            "headers": {"content-type": "application/json"},
            "duration_ms": 150.0,
        },
        "events": [
            {
                "eid": 1,
                "type": "http.client",
                "start_offset_ms": 10.0,
                "duration_ms": 100.0,
                "signature": {
                    "lib": "httpx",
                    "method": "GET",
                    "url": "https://api.example.com/data",
                    "query": {},
                },
                "result": {
                    "status": 200,
                    "headers": {"content-type": "application/json"},
                    "body": {
                        "_captured": True,
                        "encoding": "json",
                        "data": {"key": "value"},
                    },
                },
            }
        ],
        "policies": {
            "redaction": {"mode": "default", "rules": ["authorization"]},
            "capture": {"max_body_kb": 64},
            "sampling": {"rate": 1.0},
        },
        "stats": {
            "event_counts": {"http.client": 1},
            "total_events": 1,
            "total_duration_ms": 150.0,
        },
    }
