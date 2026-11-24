"""
Dispatch and Operational Control Routes (FR-3.3)
Handles:
- FR-3.3: One-Click Dispatch triggering automated simulated SMS/Voice alert to field units
- Unit fleet tracking and status management
- Incident query and filter APIs
- Incident resolution and unit release
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional, List
import time

from ..schemas import EventPayload, RescueUnit, DispatchRequest
from ..store import store
from ..websocket_manager import ws_manager
from ..security import verify_admin_token

router = APIRouter(prefix="/api", tags=["Dispatch & Ops"])

@router.post("/dispatch/{event_id}", dependencies=[Depends(verify_admin_token)])
async def dispatch_incident(event_id: str, request: Optional[DispatchRequest] = None):
    """
    FR-3.3 One-Click Dispatch Action:
    1. Operator clicks 'Dispatch' in Command Dashboard
    2. Identifies or confirms assigned field unit
    3. Sets unit status to EN_ROUTE
    4. Updates event status to 'DISPATCHED'
    5. Broadcasts real-time unit and event updates to all dashboards (<50ms)
    """
    event = store.get_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Incident event not found")

    # If specific unit requested or currently assigned
    unit_id = request.unit_id if request else None
    unit = None
    if unit_id:
        unit = store.get_unit(unit_id)

    if not unit:
        # Pick nearest matching available unit
        unit = store.find_nearest_unit(
            category=event.category,
            lat=event.coordinates.lat,
            lng=event.coordinates.lng
        )

    assigned_info = None
    if unit:
        store.update_unit_status(unit.id, "EN_ROUTE")
        assigned_info = {
            "id": unit.id,
            "name": unit.name,
            "unit_type": unit.unit_type,
            "contact": unit.contact,
            "eta_minutes": unit.eta_minutes,
            "status": "EN_ROUTE"
        }
        event.assigned_unit = assigned_info
        # Broadcast unit status change
        await ws_manager.broadcast_unit_update(unit.model_dump())

    event.status = "DISPATCHED"
    event.verified = True

    # Broadcast updated event to WebSocket
    await ws_manager.broadcast_event(event.model_dump())

    if assigned_info:
        await ws_manager.broadcast_dispatch_alert(event.id, assigned_info)

    # Simulated SMS/Voice Dispatch Notification log
    simulated_sms = {
        "to": unit.contact if unit else "+91-9876543210",
        "message": f"🚨 [RESCUENET-X DISPATCH] Priority Alert: {event.category} at {event.sector}. Severity {event.severity}/10. Casualties: {event.casualty_count}. Summary: {event.summary}",
        "timestamp": time.time(),
        "dispatched_by": "Operator 1-Click Action"
    }

    return {
        "status": "dispatched",
        "event_id": event.id,
        "assigned_unit": assigned_info,
        "notification_dispatched": simulated_sms
    }

@router.post("/events/{event_id}/resolve", dependencies=[Depends(verify_admin_token)])
async def resolve_incident(event_id: str):
    """
    Frees the assigned unit (sets status back to AVAILABLE), marks the incident RESOLVED,
    and broadcasts UNIT_UPDATE and INCIDENT_UPDATE over WebSocket.
    """
    event = store.get_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Incident event not found")

    event.status = "RESOLVED"

    freed_unit = None
    if event.assigned_unit and "id" in event.assigned_unit:
        unit_id = event.assigned_unit["id"]
        store.update_unit_status(unit_id, "AVAILABLE")
        unit_obj = store.get_unit(unit_id)
        if unit_obj:
            freed_unit = unit_obj.model_dump()
            await ws_manager.broadcast_unit_update(freed_unit)

    await ws_manager.broadcast_event(event.model_dump())

    return {
        "status": "resolved",
        "event_id": event.id,
        "event": event.model_dump(),
        "freed_unit": freed_unit
    }

@router.get("/events")
async def list_events(
    category: Optional[str] = Query(None),
    min_severity: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    limit: Optional[int] = Query(None, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    """Lists events with optional filtering and pagination."""
    # Handle direct function calls where defaults are Query objects
    if not isinstance(offset, int):
        offset = 0
    if not isinstance(limit, int):
        limit = None
    if not isinstance(category, str):
        category = None
    if not isinstance(min_severity, int):
        min_severity = None
    if not isinstance(status, str):
        status = None

    events = store.list_events()

    if category:
        events = [e for e in events if e.category.upper() == category.upper()]
    if min_severity:
        events = [e for e in events if e.severity >= min_severity]
    if status:
        events = [e for e in events if e.status.upper() == status.upper()]

    total = len(events)
    if limit is not None:
        paged = events[offset:offset + limit]
    else:
        paged = events[offset:]

    return {"events": [e.model_dump() for e in paged], "total": total}

@router.get("/events/{event_id}")
async def get_event(event_id: str):
    """Fetches details for a single incident."""
    event = store.get_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Incident not found")
    return event.model_dump()

@router.get("/units")
async def list_units():
    """Returns all rescue response units in fleet."""
    units = store.list_units()
    return {"units": [u.model_dump() for u in units]}
