"""
Visual Incident Verification and Digital/PWA Report Routes (FR-2)
Handles:
- FR-2.1: Image Classification (Flood, Fire, Collapse) with two-tier confidence logic
- FR-2.2: Dynamic Severity Scoring
- FR-2.3: Perceptual Hashing (pHash) Deduplication within 500m, same category, 30m window
- Phase 2.6: File upload header sniffing, max 8MB limit, safe server-generated extension
- Phase 2.8: Rate limiting per IP
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request
import shutil
import uuid
import os
import random
from typing import Optional

from ..config import IMAGE_UPLOAD_DIR, DEFAULT_CENTER_LAT, DEFAULT_CENTER_LNG
from ..schemas import EventPayload, Coordinates, PWAReportRequest
from ..vision_engine import analyze_visual_disaster
from ..agentic_dispatcher import run_agentic_pipeline
from ..websocket_manager import ws_manager
from ..security import validate_image_upload, citizen_report_limiter

router = APIRouter(prefix="/api/report", tags=["Incident Reports"])

@router.post("/visual")
async def report_visual(
    request: Request,
    image: UploadFile = File(...),
    lat: Optional[float] = Form(None),
    lng: Optional[float] = Form(None),
    sector: Optional[str] = Form("Sector 4 - Commercial Zone")
):
    """
    Visual incident verification endpoint with content sniffing, size checks, and rate limiting.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    citizen_report_limiter.check(client_ip)

    # Read image bytes and sniff MIME / format
    content = await image.read()
    safe_ext = validate_image_upload(content)

    filename = f"{uuid.uuid4().hex[:12]}{safe_ext}"
    saved_path = str(IMAGE_UPLOAD_DIR / filename)

    try:
        with open(saved_path, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to persist validated image artifact: {e}")

    # Analyze image with Vision Engine
    vision_result = analyze_visual_disaster(saved_path)

    is_loc_unknown = False
    if lat is not None and lng is not None:
        event_lat, event_lng = float(lat), float(lng)
    else:
        is_loc_unknown = True
        event_lat = DEFAULT_CENTER_LAT + random.uniform(-0.010, 0.010)
        event_lng = DEFAULT_CENTER_LNG + random.uniform(-0.010, 0.010)

    # Build canonical Section 4.5 event payload
    event_payload = EventPayload(
        category=vision_result["category"],
        coordinates=Coordinates(lat=round(event_lat, 6), lng=round(event_lng, 6)),
        sector=sector or "Sector 4 - Commercial Zone",
        severity=vision_result["severity"],
        casualty_count=vision_result.get("person_count", 0),
        summary=vision_result["summary"],
        confidence=vision_result["confidence"],
        source="image",
        raw_transcript=None,
        verified=vision_result["verified"],
        status=vision_result["status"],
        phash=vision_result["phash"],
        image_url=f"/uploads/images/{filename}",
        location_unknown=is_loc_unknown
    )

    # Run agentic pipeline (deduplication, urgency score, nearest-unit routing)
    final_event, state = run_agentic_pipeline(event_payload)

    # Broadcast canonical payload via WebSocket (< 50ms)
    await ws_manager.broadcast_event(final_event.model_dump())

    return {
        "status": "success",
        "event": final_event.model_dump(),
        "is_duplicate": state.is_duplicate,
        "logs": state.action_log
    }

@router.post("/pwa")
async def report_pwa(request: Request, report: PWAReportRequest):
    """
    Offline PWA Mesh report submission endpoint with rate limiting.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    citizen_report_limiter.check(client_ip)

    event_payload = EventPayload(
        category=report.category,
        coordinates=Coordinates(lat=report.lat, lng=report.lng),
        sector=report.sector or "Civilian PWA Mesh Node",
        severity=report.severity,
        casualty_count=report.casualty_count,
        summary=f"Citizen PWA Report: {report.description}",
        confidence=0.85,
        source="pwa",
        raw_transcript=report.description,
        verified=True
    )

    final_event, state = run_agentic_pipeline(event_payload)
    await ws_manager.broadcast_event(final_event.model_dump())

    return {
        "status": "success",
        "event": final_event.model_dump(),
        "is_duplicate": state.is_duplicate
    }
