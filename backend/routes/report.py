"""
Visual Incident Verification and Digital/PWA Report Routes (FR-2)
Handles:
- FR-2.1: Image Classification (Flood, Fire, Collapse) with two-tier confidence logic
- FR-2.2: Dynamic Severity Scoring
- FR-2.3: Perceptual Hashing (pHash) Deduplication within 500m & Hamming < 5
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
import shutil
import uuid
import os
from typing import Optional

from ..config import IMAGE_UPLOAD_DIR, DEFAULT_CENTER_LAT, DEFAULT_CENTER_LNG
from ..schemas import EventPayload, Coordinates, PWAReportRequest
from ..vision_engine import analyze_visual_disaster
from ..agentic_dispatcher import run_agentic_pipeline
from ..websocket_manager import ws_manager

router = APIRouter(prefix="/api/report", tags=["Incident Reports"])

@router.post("/visual")
async def report_visual(
    image: UploadFile = File(...),
    lat: Optional[float] = Form(None),
    lng: Optional[float] = Form(None),
    sector: Optional[str] = Form("Sector 4 - Commercial Zone")
):
    """
    FR-2.1, FR-2.2, FR-2.3:
    Visual incident verification endpoint:
    1. Receives image upload
    2. Runs Computer Vision classification (Flood, Fire, Collapse)
    3. Computes pHash and checks for duplicate images (< 500m, Hamming < 5)
    4. Evaluates two-tier confidence thresholds:
       - < 0.70: MANUAL_REVIEW, not auto-dispatched
       - >= 0.70 and < 0.85: DISPATCHED, unverified/low-confidence
       - >= 0.85: DISPATCHED, verified
    5. Dispatches nearest unit and streams via WebSocket
    """
    # Generate unique filename preserving extension
    ext = os.path.splitext(image.filename)[1] or ".jpg"
    filename = f"{uuid.uuid4().hex[:10]}{ext}"
    saved_path = str(IMAGE_UPLOAD_DIR / filename)

    try:
        with open(saved_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save image upload: {e}")

    # Analyze image with Vision Engine
    vision_result = analyze_visual_disaster(saved_path)

    # Coordinates fallback around default center if not supplied
    event_lat = lat if lat is not None else (DEFAULT_CENTER_LAT - 0.003)
    event_lng = lng if lng is not None else (DEFAULT_CENTER_LNG + 0.005)

    # Build canonical Section 4.5 event payload
    event_payload = EventPayload(
        category=vision_result["category"],
        coordinates=Coordinates(lat=event_lat, lng=event_lng),
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
        image_url=f"/uploads/images/{filename}"
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
async def report_pwa(report: PWAReportRequest):
    """
    Offline PWA Mesh report submission endpoint.
    Handles digital incident reports submitted by citizens via web app or local hotspot mesh.
    """
    event_payload = EventPayload(
        category=report.category.upper(),
        coordinates=Coordinates(lat=report.lat, lng=report.lng),
        sector=report.sector or "Civilian PWA Mesh Node",
        severity=report.severity,
        casualty_count=report.casualty_count,
        summary=f"Citizen PWA Report: {report.description}",
        confidence=0.88,
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
