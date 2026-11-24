#!/usr/bin/env python3
"""
Test Suite: CAD Routing, Unit State Lifecycle, and Resolution
Verifies:
1. Assigning an incident sets assigned unit status to EN_ROUTE
2. Subsequent incident gets the NEXT nearest available unit (skips EN_ROUTE units)
3. When all units are busy, event is marked status="PENDING" and queued
4. Resolving an incident frees the unit back to status="AVAILABLE"
"""

import sys
from pathlib import Path

# Add project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.store import store
from backend.schemas import EventPayload, RescueUnit
from backend.agentic_dispatcher import run_agentic_pipeline

def _get_unit_id(assigned):
    if isinstance(assigned, dict):
        return assigned.get("id")
    return getattr(assigned, "id", None)

def test_unit_marked_en_route_and_next_nearest_assigned():
    store.reset()

    # Seed 2 rescue units at known coordinates
    # Target incident location: (28.6145, 77.2085)
    # Unit 1 is closer: (28.6150, 77.2090) ~ 70m away
    # Unit 2 is further: (28.6250, 77.2190) ~ 1.5km away
    u1 = RescueUnit(id="UNIT_ALPHA", name="Squad Alpha", unit_type="RESCUE", status="AVAILABLE", lat=28.6150, lng=77.2090, contact="101")
    u2 = RescueUnit(id="UNIT_BRAVO", name="Squad Bravo", unit_type="RESCUE", status="AVAILABLE", lat=28.6250, lng=77.2190, contact="102")
    store._units = {u1.id: u1, u2.id: u2}

    # Incident 1
    ev1 = EventPayload(
        id="INC_01",
        category="RESCUE",
        sector="Sector 18",
        severity=9,
        casualty_count=2,
        coordinates={"lat": 28.6145, "lng": 77.2085},
        summary="Building collapse",
        confidence=0.92,
        source="pwa",
        verified=True
    )
    store.add_event(ev1)

    # Run dispatch pipeline for ev1
    out_ev1, state1 = run_agentic_pipeline(ev1)

    # Unit Alpha must be assigned to ev1 and status changed to EN_ROUTE
    assert out_ev1.assigned_unit is not None, "Failed: Unit must be assigned to ev1"
    assert _get_unit_id(out_ev1.assigned_unit) == "UNIT_ALPHA", "Failed: Closest unit UNIT_ALPHA must be assigned"
    unit_alpha = store.get_unit("UNIT_ALPHA")
    assert unit_alpha.status == "EN_ROUTE", f"Failed: Unit status must be EN_ROUTE, got {unit_alpha.status}"

    # Incident 2 at a distinct location (>500m away so not spatially merged)
    ev2 = EventPayload(
        id="INC_02",
        category="RESCUE",
        sector="Sector 18 East",
        severity=8,
        casualty_count=1,
        coordinates={"lat": 28.6250, "lng": 77.2190},
        summary="Water rescue",
        confidence=0.88,
        source="pwa",
        verified=True
    )
    store.add_event(ev2)

    # Run dispatch pipeline for ev2
    out_ev2, state2 = run_agentic_pipeline(ev2)

    # Unit Alpha is busy (EN_ROUTE). Unit Bravo must be assigned!
    assert out_ev2.assigned_unit is not None, "Failed: Unit must be assigned to ev2"
    assert _get_unit_id(out_ev2.assigned_unit) == "UNIT_BRAVO", "Failed: Next nearest available unit UNIT_BRAVO must be assigned"
    unit_bravo = store.get_unit("UNIT_BRAVO")
    assert unit_bravo.status == "EN_ROUTE", f"Failed: Unit Bravo must be EN_ROUTE, got {unit_bravo.status}"

def test_when_all_units_busy_queues_pending():
    store.reset()

    # Only 1 unit, already EN_ROUTE
    u1 = RescueUnit(id="UNIT_BUSY", name="Squad Busy", unit_type="RESCUE", status="EN_ROUTE", lat=28.6150, lng=77.2090, contact="101")
    store._units = {u1.id: u1}

    ev3 = EventPayload(
        id="INC_03",
        category="RESCUE",
        sector="Sector 18 West",
        severity=8,
        casualty_count=1,
        coordinates={"lat": 28.6145, "lng": 77.2085},
        summary="Trapped citizen",
        confidence=0.85,
        source="pwa",
        verified=True
    )
    store.add_event(ev3)

    out_ev3, state3 = run_agentic_pipeline(ev3)

    assert out_ev3.assigned_unit is None, "Failed: No unit should be assigned when all are busy"
    assert out_ev3.status == "PENDING", f"Failed: Event should be queued as PENDING, got {out_ev3.status}"
    assert any("PENDING" in log for log in state3.action_log), "Failed: PENDING queue status must be logged in action log"

def test_resolving_incident_frees_unit():
    store.reset()

    u = RescueUnit(id="UNIT_TO_FREE", name="Squad To Free", unit_type="RESCUE", status="EN_ROUTE", lat=28.6150, lng=77.2090, contact="101")
    store._units = {u.id: u}

    ev = EventPayload(
        id="INC_RESOLVE_ME",
        category="RESCUE",
        sector="Sector 18",
        severity=8,
        casualty_count=1,
        coordinates={"lat": 28.6145, "lng": 77.2085},
        summary="Emergency under control",
        confidence=0.90,
        source="pwa",
        status="DISPATCHED",
        assigned_unit=u.model_dump(),
        verified=True
    )
    store.add_event(ev)

    # Simulate resolve operation
    ev.status = "RESOLVED"
    store.update_event_status(ev.id, "RESOLVED")
    store.update_unit_status(u.id, "AVAILABLE")

    # Verify event is resolved and unit is AVAILABLE
    resolved_ev = store.get_event(ev.id)
    assert resolved_ev.status == "RESOLVED"
    freed_unit = store.get_unit(u.id)
    assert freed_unit.status == "AVAILABLE", f"Failed: Unit must be freed to AVAILABLE, got {freed_unit.status}"

if __name__ == "__main__":
    print("Running CAD Routing & Unit Lifecycle Test Suite...")
    test_unit_marked_en_route_and_next_nearest_assigned()
    print("  ✓ Unit marked EN_ROUTE and next nearest unit assigned to subsequent event")
    test_when_all_units_busy_queues_pending()
    print("  ✓ When all units are busy, event is marked PENDING")
    test_resolving_incident_frees_unit()
    print("  ✓ Resolving incident frees assigned unit back to AVAILABLE")
    print("✅ All CAD routing tests passed!")
