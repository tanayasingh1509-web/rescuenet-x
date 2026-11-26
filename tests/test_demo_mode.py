#!/usr/bin/env python3
"""
Test Suite: DEMO_MODE and Operator Authorization Isolation
Verifies:
1. Strict mode (DEMO_MODE=false/unset) returns 401 on /api/dispatch/{id}, /api/events/{id}/resolve, /api/simulate/reset without token
2. Strict mode accepts valid X-Admin-Token or Bearer token
3. DEMO_MODE=true allows unauthenticated access to dispatch, resolve, and reset
4. DEMO_MODE=true STILL strictly rejects GET and POST /api/config/keys with 401 without admin token
"""

import os
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Add project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.main import app
from backend.config import ADMIN_TOKEN
from backend.store import store
from backend.schemas import EventPayload, Coordinates

@pytest.fixture(autouse=True)
def clean_demo_mode():
    """Ensure DEMO_MODE is cleaned up after each test."""
    original = os.environ.get("DEMO_MODE")
    yield
    if original is not None:
        os.environ["DEMO_MODE"] = original
    else:
        os.environ.pop("DEMO_MODE", None)

def test_strict_mode_rejects_unauthenticated():
    os.environ["DEMO_MODE"] = "false"

    with TestClient(app) as client:
        # Get seeded event from lifespan
        events = store.list_events()
        event_id = events[0].id if events else "test-incident-1"

        # 1. Dispatch without token -> 401
        res = client.post(f"/api/dispatch/{event_id}", json={"event_id": event_id})
        assert res.status_code == 401, f"Expected 401, got {res.status_code}"

        # 2. Resolve without token -> 401
        res = client.post(f"/api/events/{event_id}/resolve")
        assert res.status_code == 401, f"Expected 401, got {res.status_code}"

        # 3. Simulate reset without token -> 401
        res = client.post("/api/simulate/reset")
        assert res.status_code == 401, f"Expected 401, got {res.status_code}"

def test_strict_mode_accepts_valid_token():
    os.environ["DEMO_MODE"] = "false"

    with TestClient(app) as client:
        events = store.list_events()
        event_id = events[0].id if events else "test-incident-1"

        headers = {"X-Admin-Token": ADMIN_TOKEN}

        # 1. Dispatch with token -> 200
        res = client.post(f"/api/dispatch/{event_id}", json={"event_id": event_id}, headers=headers)
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"

        # 2. Resolve with token -> 200
        res = client.post(f"/api/events/{event_id}/resolve", headers=headers)
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"

        # 3. Reset with token -> 200
        res = client.post("/api/simulate/reset", headers=headers)
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"

def test_demo_mode_opens_operator_routes():
    os.environ["DEMO_MODE"] = "true"

    with TestClient(app) as client:
        # Re-seed test event if needed
        if not store.list_events():
            store.add_event(EventPayload(
                category="FIRE",
                coordinates=Coordinates(lat=28.6139, lng=77.2090),
                sector="Central Plaza",
                severity=7,
                casualty_count=1,
                summary="Transformer fire near substation",
                confidence=0.88,
                source="operator"
            ))
        events = store.list_events()
        event_id = events[0].id

        # 1. Dispatch without token in DEMO_MODE -> 200
        res = client.post(f"/api/dispatch/{event_id}", json={"event_id": event_id})
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"

        # 2. Resolve without token in DEMO_MODE -> 200
        res = client.post(f"/api/events/{event_id}/resolve")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"

        # 3. Reset without token in DEMO_MODE -> 200
        res = client.post("/api/simulate/reset")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"

def test_demo_mode_still_protects_config_keys():
    os.environ["DEMO_MODE"] = "true"

    with TestClient(app) as client:
        # 1. GET /api/config/keys without token -> MUST be 401 even in DEMO_MODE
        res = client.get("/api/config/keys")
        assert res.status_code == 401, f"Expected 401 for GET /api/config/keys in DEMO_MODE, got {res.status_code}"

        # 2. POST /api/config/keys without token -> MUST be 401 even in DEMO_MODE
        res = client.post("/api/config/keys", json={"gemini_api_key": "test_fake_key"})
        assert res.status_code == 401, f"Expected 401 for POST /api/config/keys in DEMO_MODE, got {res.status_code}"

        # 3. Valid token on /api/config/keys -> 200
        res = client.get("/api/config/keys", headers={"X-Admin-Token": ADMIN_TOKEN})
        assert res.status_code == 200, f"Expected 200 with admin token, got {res.status_code}"
