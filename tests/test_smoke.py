#!/usr/bin/env python3
"""
RescueNet-X End-to-End System Smoke Test
Exercises the complete incident lifecycle:
1. Verifies system health check (/health)
2. Resets CAD incident store to baseline (/api/simulate/reset)
3. Injects live flood disaster scenario (/api/simulate/scenario/flood)
4. Verifies incident appears in CAD queue and unit is assigned
5. Authorizes CAD unit dispatch (/api/dispatch/{event_id})
6. Confirms assigned unit state transitions to EN_ROUTE
7. Resolves incident (/api/events/{event_id}/resolve)
8. Confirms unit is freed back to AVAILABLE
"""

import sys
from pathlib import Path

# Add project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.store import store
from backend.schemas import DispatchRequest
from backend.routes.simulate import reset_store, trigger_scenario
from backend.routes.dispatch import list_events, dispatch_incident, resolve_incident
from backend.main import health_check
from backend.websocket_manager import ws_manager

# Mock WebSocket broadcasts for smoke test isolation without proactor loop
async def _noop(*args, **kwargs):
    return None

ws_manager.broadcast_event = _noop
ws_manager.broadcast_unit_update = _noop
ws_manager.broadcast_dispatch_alert = _noop

def _run_coro(coro):
    """Run synchronous coroutine without spawning Windows socketpair loop."""
    try:
        coro.send(None)
    except StopIteration as e:
        return e.value
    raise RuntimeError("Coroutine did not complete synchronously")

def run_smoke_test():
    print("=" * 60)
    print("RESCUENET-X END-TO-END SMOKE TEST")
    print("=" * 60)

    # 1. Health check
    print("\n[Step 1] Checking system health status (/health)...")
    health = _run_coro(health_check())
    assert health["status"] == "healthy", f"Expected healthy, got {health['status']}"
    assert "database" in health, "database status missing from health check"
    assert health["database"] == "connected", f"Expected db connected, got {health['database']}"
    print(f"  ✓ System healthy: DB {health['database']}, Version: {health['version']}")

    # 2. Reset CAD store with admin auth
    print("\n[Step 2] Resetting CAD store to baseline (/api/simulate/reset)...")
    reset_res = _run_coro(reset_store())
    assert reset_res["status"] == "reset_successful", f"Expected reset_successful, got {reset_res['status']}"
    initial_events = _run_coro(list_events())
    assert len(initial_events["events"]) == 0, "Store should be empty after reset"
    print("  ✓ Store reset clean. 0 active incidents.")

    # 3. Inject flood crisis scenario
    print("\n[Step 3] Triggering flood disaster scenario (/api/simulate/scenario/flood)...")
    flood_res = _run_coro(trigger_scenario("flood"))
    assert flood_res["status"] == "success", f"Expected success, got {flood_res['status']}"
    event = flood_res["event"]
    assert event["category"] == "FLOOD", f"Expected FLOOD, got {event['category']}"
    event_id = event["id"]
    print(f"  ✓ Scenario injected: Incident #{event_id} ({event['category']} - {event['sector']})")

    # 4. Verify incident appears on CAD queue
    print("\n[Step 4] Verifying incident appears in CAD queue (/api/events)...")
    events_res = _run_coro(list_events())
    found = any(e["id"] == event_id for e in events_res["events"])
    assert found, f"Incident {event_id} not found in CAD events list"
    print(f"  ✓ Incident #{event_id} verified present in live CAD incident queue")

    # 5. Authorize unit dispatch
    print(f"\n[Step 5] Authorizing unit dispatch (/api/dispatch/{event_id})...")
    req = DispatchRequest(event_id=event_id, operator_notes="Authorize immediate tactical dispatch")
    dispatch_res = _run_coro(dispatch_incident(event_id=event_id, request=req))
    assert dispatch_res["status"] == "dispatched", f"Expected dispatched, got {dispatch_res['status']}"
    assigned_unit = dispatch_res["assigned_unit"]
    assigned_unit_id = assigned_unit["id"] if isinstance(assigned_unit, dict) else assigned_unit.id
    print(f"  ✓ Dispatch confirmed. Unit assigned: {assigned_unit_id}")

    # 6. Verify unit status is EN_ROUTE
    print(f"\n[Step 6] Verifying unit #{assigned_unit_id} status is EN_ROUTE...")
    unit = store.get_unit(assigned_unit_id)
    assert unit.status == "EN_ROUTE", f"Expected EN_ROUTE, got {unit.status}"
    print(f"  ✓ Unit #{assigned_unit_id} confirmed in EN_ROUTE state")

    # 7. Resolve incident
    print(f"\n[Step 7] Resolving incident #{event_id} (/api/events/{event_id}/resolve)...")
    resolve_res = _run_coro(resolve_incident(event_id=event_id))
    assert resolve_res["status"] == "resolved", f"Expected resolved, got {resolve_res['status']}"
    print(f"  ✓ Incident #{event_id} marked RESOLVED")

    # 8. Confirm unit is freed back to AVAILABLE
    print(f"\n[Step 8] Confirming unit #{assigned_unit_id} is freed to AVAILABLE...")
    freed_unit = store.get_unit(assigned_unit_id)
    assert freed_unit.status == "AVAILABLE", f"Expected AVAILABLE, got {freed_unit.status}"
    print(f"  ✓ Unit #{assigned_unit_id} successfully freed back to AVAILABLE")

    print("\n" + "=" * 60)
    print("✅ SMOKE TEST PASSED: Full Incident Lifecycle Verified!")
    print("=" * 60)

if __name__ == "__main__":
    run_smoke_test()
