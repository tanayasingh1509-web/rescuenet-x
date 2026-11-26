"""
Demo-mode access control:
- DEMO_MODE off  -> dispatch/resolve/reset require ADMIN_TOKEN (strict, default)
- DEMO_MODE on   -> those operational routes work without a token
- /api/config/*  -> ALWAYS requires ADMIN_TOKEN, regardless of DEMO_MODE
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.config import ADMIN_TOKEN
from backend.store import store

@pytest.fixture(scope="module")
def client():
    # `with` runs the app lifespan, which seeds the baseline incident
    with TestClient(app) as c:
        yield c


def _first_event_id():
    events = store.list_events()
    assert events, "seed event expected"
    return events[0].id


def test_strict_mode_blocks_operational_routes(client, monkeypatch):
    monkeypatch.delenv("DEMO_MODE", raising=False)
    eid = _first_event_id()
    assert client.post(f"/api/dispatch/{eid}").status_code == 401
    assert client.post(f"/api/events/{eid}/resolve").status_code == 401
    assert client.post("/api/simulate/reset").status_code == 401


def test_strict_mode_accepts_valid_token(client, monkeypatch):
    monkeypatch.delenv("DEMO_MODE", raising=False)
    eid = _first_event_id()
    res = client.post(f"/api/dispatch/{eid}", headers={"X-Admin-Token": ADMIN_TOKEN})
    assert res.status_code == 200


def test_demo_mode_opens_operational_routes(client, monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    eid = _first_event_id()
    assert client.post(f"/api/dispatch/{eid}").status_code == 200
    assert client.post(f"/api/events/{eid}/resolve").status_code == 200


def test_demo_mode_never_unlocks_config(client, monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    assert client.get("/api/config/keys").status_code == 401
    res = client.post("/api/config/keys", json={"gemini_api_key": "x"})
    assert res.status_code == 401
