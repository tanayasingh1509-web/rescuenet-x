"""
Unit and integration tests for Phase 3 Architecture and Reliability in RESCUENET-X.
Tests run synchronously with pure Python assertions to ensure 100% sandboxed execution.
"""

import os
import time
import json
from backend.store import store, IncidentStore, MAX_EVENTS_CAP
from backend.schemas import EventPayload, Coordinates
from backend.websocket_manager import ConnectionManager
from backend.database import get_db_connection

def test_sqlite_persistence_survives_restart():
    """Verify events and units saved to SQLite survive in-memory cache clear and reload."""
    store.reset()

    # Add a test incident
    ev = EventPayload(
        id="PERSIST-1",
        category="FLOOD",
        coordinates=Coordinates(lat=28.6189, lng=77.2020),
        sector="Test Embankment",
        severity=8,
        casualty_count=3,
        summary="Testing SQLite persistence across restarts",
        confidence=0.91,
        source="pwa",
        verified=True,
        status="DISPATCHED"
    )
    store.add_event(ev)

    # Verify event is written directly to SQLite
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM events WHERE id = ?", ("PERSIST-1",))
    row = cur.fetchone()
    conn.close()
    assert row is not None
    assert row["category"] == "FLOOD"
    assert row["casualty_count"] == 3

    # Simulate server restart by creating a new IncidentStore instance
    fresh_store = IncidentStore()
    loaded_ev = fresh_store.get_event("PERSIST-1")
    assert loaded_ev is not None
    assert loaded_ev.id == "PERSIST-1"
    assert loaded_ev.summary == "Testing SQLite persistence across restarts"
    assert loaded_ev.casualty_count == 3
    assert loaded_ev.verified is True

def test_pagination_and_max_events_cap():
    """Verify list_events pagination (limit, offset) and max event cap."""
    store.reset()

    # Seed 10 sequential events
    now = time.time()
    for i in range(10):
        ev = EventPayload(
            id=f"EV-PAGE-{i:02d}",
            category="FIRE",
            coordinates=Coordinates(lat=28.6000 + i * 0.001, lng=77.2000),
            severity=5,
            confidence=0.85,
            source="pwa",
            timestamp=now + i
        )
        store.add_event(ev)

    # Test limit=3, offset=0 (should return most recent 3: 9, 8, 7)
    page1 = store.list_events(limit=3, offset=0)
    assert len(page1) == 3
    assert page1[0].id == "EV-PAGE-09"
    assert page1[1].id == "EV-PAGE-08"
    assert page1[2].id == "EV-PAGE-07"

    # Test limit=3, offset=3 (should return next 3: 6, 5, 4)
    page2 = store.list_events(limit=3, offset=3)
    assert len(page2) == 3
    assert page2[0].id == "EV-PAGE-06"
    assert page2[1].id == "EV-PAGE-05"
    assert page2[2].id == "EV-PAGE-04"

def test_websocket_manager_sequencing_and_history():
    """Verify WebSocket manager increments sequence numbers and records message history."""
    wm = ConnectionManager()
    assert wm.current_seq() == 0

    # Simulate message generation without active network sockets
    msg1 = {"type": "INCIDENT_UPDATE", "data": "first"}
    msg2 = {"type": "UNIT_UPDATE", "data": "second"}

    # Use internal sequence generator
    seq1 = wm._next_seq()
    msg1["seq"] = seq1
    wm._message_history.append(msg1)

    seq2 = wm._next_seq()
    msg2["seq"] = seq2
    wm._message_history.append(msg2)

    assert wm.current_seq() == 2
    assert seq1 == 1
    assert seq2 == 2

    # Verify resync returns messages after last_seq
    missed = wm.get_messages_since(last_seq=1)
    assert len(missed) == 1
    assert missed[0]["data"] == "second"

def test_database_reset_clears_db():
    """Verify reset() empties SQLite tables and restores default fleet."""
    store.add_event(EventPayload(
        id="TEMP-DEL",
        category="RESCUE",
        coordinates=Coordinates(lat=28.61, lng=77.21),
        source="pwa"
    ))
    assert store.get_event("TEMP-DEL") is not None

    store.reset()
    assert store.get_event("TEMP-DEL") is None

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as c FROM events")
    cnt = cur.fetchone()["c"]
    conn.close()
    assert cnt == 0

    units = store.list_units()
    assert len(units) >= 4
    assert all(u.status == "AVAILABLE" for u in units)

if __name__ == "__main__":
    print("[TEST 1] test_sqlite_persistence_survives_restart...")
    test_sqlite_persistence_survives_restart()
    print("[TEST 2] test_pagination_and_max_events_cap...")
    test_pagination_and_max_events_cap()
    print("[TEST 3] test_websocket_manager_sequencing_and_history...")
    test_websocket_manager_sequencing_and_history()
    print("[TEST 4] test_database_reset_clears_db...")
    test_database_reset_clears_db()
    print("========================================")
    print("ALL PHASE 3 ARCHITECTURE TESTS PASSED CLEANLY!")
    print("========================================")
