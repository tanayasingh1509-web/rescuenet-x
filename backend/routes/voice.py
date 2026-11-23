"""
Twilio VoiceBridge Telephony Routes (FR-1)
Handles:
- FR-1.1: DTMF Interactive Menu (1: Police, 2: Ambulance, 3: Rescue) with Sector lookup
- FR-1.2: Speech Capture & Whisper STT
- FR-1.3: Entity Extraction & Structured Payload Broadcast
- Location resolution via sector lookup or non-merging jitter coordinates
"""

from fastapi import APIRouter, Request, Response, Form, UploadFile, File
from fastapi.responses import PlainTextResponse
import os
import time
import requests
import uuid
import random
from typing import Optional, Tuple
from twilio.twiml.voice_response import VoiceResponse, Gather

from ..config import AUDIO_UPLOAD_DIR, DEFAULT_CENTER_LAT, DEFAULT_CENTER_LNG
from ..schemas import EventPayload, Coordinates
from ..ai_engine import process_audio_transcript
from ..agentic_dispatcher import run_agentic_pipeline
from ..websocket_manager import ws_manager

router = APIRouter(prefix="/api/voice", tags=["Voice Telephony"])

# Configurable sector / landmark lookup table
SECTOR_LOOKUP = {
    "1": ("Sector 18 River Basin", 28.6189, 77.2020),
    "2": ("Central Municipal Market", 28.6089, 77.2170),
    "3": ("Industrial Sector 7", 28.6250, 77.2190),
    "4": ("Civic Infrastructure Zone", 28.6050, 77.2010),
    "river": ("Sector 18 River Basin", 28.6189, 77.2020),
    "market": ("Central Municipal Market", 28.6089, 77.2170),
    "industrial": ("Industrial Sector 7", 28.6250, 77.2190),
    "civic": ("Civic Infrastructure Zone", 28.6050, 77.2010),
    "commercial": ("Commercial Sector 4", 28.6120, 77.2150)
}

def resolve_voice_coordinates(
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    sector_input: Optional[str] = None
) -> Tuple[float, float, str, bool]:
    """
    Resolves caller coordinates:
    1. If lat/lng supplied, validates and uses them directly.
    2. If sector/landmark matches lookup table, returns designated coordinates.
    3. Otherwise, generates a jittered point near city center to avoid cluster merging,
       flagging location_unknown=True.
    """
    if lat is not None and lng is not None:
        try:
            f_lat, f_lng = float(lat), float(lng)
            if -90.0 <= f_lat <= 90.0 and -180.0 <= f_lng <= 180.0:
                sec = sector_input or "Reported Geolocation"
                return f_lat, f_lng, sec, False
        except (ValueError, TypeError):
            pass

    if sector_input:
        s_lower = str(sector_input).lower().strip()
        for key, (name, s_lat, s_lng) in SECTOR_LOOKUP.items():
            if key in s_lower or s_lower in key:
                return s_lat, s_lng, name, False

    # Jitter point (+/- 0.005 to 0.015 degrees) so separate callers never collide
    jitter_lat = DEFAULT_CENTER_LAT + random.uniform(-0.012, 0.012)
    jitter_lng = DEFAULT_CENTER_LNG + random.uniform(-0.012, 0.012)
    sec_name = sector_input if sector_input else "Unknown Sector (Cell Jittered)"
    return round(jitter_lat, 6), round(jitter_lng, 6), sec_name, True

@router.post("/incoming")
async def voice_incoming(request: Request):
    """
    FR-1.1 DTMF Interactive Menu:
    - Press 1 -> Police
    - Press 2 -> Ambulance / Medical
    - Press 3 -> Trapped / Rescue
    - Allows sector digit 1-4
    - If no key pressed -> capture free-form voice message (FR-1.2)
    """
    response = VoiceResponse()

    # Create Gather verb for DTMF keypad input (timeout 4 seconds)
    gather = Gather(
        num_digits=2,
        action="/api/voice/menu-select",
        method="POST",
        timeout=4
    )
    gather.say(
        "Welcome to RescueNet X Emergency Response. "
        "Press 1 for Police. "
        "Press 2 for Ambulance and Medical. "
        "Press 3 for Trapped or Search and Rescue. "
        "You may also enter your sector digit 1 to 4. "
        "Or stay on the line to speak your emergency report after the beep.",
        voice="Polly.Joanna"
    )
    response.append(gather)

    # FR-1.2: If no key pressed, record free-form voice message
    response.say("Recording your voice report now. Please speak clearly after the tone.", voice="Polly.Joanna")
    response.record(
        action="/api/voice/process-audio",
        method="POST",
        max_length=20,
        play_beep=True,
        finish_on_key="#",
        trim="trim-silence"
    )
    response.say("Thank you. Your voice report is being processed by the disaster intelligence network.", voice="Polly.Joanna")
    response.hangup()

    return Response(content=str(response), media_type="application/xml")

@router.post("/menu-select")
async def voice_menu_select(
    Digits: Optional[str] = Form(None),
    From: Optional[str] = Form("+919999000000"),
    CallSid: Optional[str] = Form(None),
    lat: Optional[float] = Form(None),
    lng: Optional[float] = Form(None),
    sector: Optional[str] = Form(None)
):
    """
    Handles keypad DTMF digit selection:
    1 -> Police
    2 -> Ambulance
    3 -> Trapped / Rescue
    Optional 2nd digit -> Sector (1 to 4)
    """
    response = VoiceResponse()
    digits = Digits or "3"
    primary_digit = digits[0]
    sector_digit = digits[1] if len(digits) > 1 else sector

    cat_map = {
        "1": ("POLICE", "Police Emergency", 8),
        "2": ("AMBULANCE", "Medical Ambulance Priority", 8),
        "3": ("RESCUE", "Trapped / Search & Rescue Squad", 9)
    }

    category, desc, severity = cat_map.get(primary_digit, ("RESCUE", "General Crisis Rescue", 7))

    response.say(f"Emergency received for {desc}. Immediate dispatch initiated. Stay on the line or move to safe ground.", voice="Polly.Joanna")
    response.hangup()

    # Resolve coordinates via sector lookup or jitter
    ev_lat, ev_lng, sec_name, is_loc_unknown = resolve_voice_coordinates(
        lat=lat,
        lng=lng,
        sector_input=sector_digit
    )

    event_payload = EventPayload(
        category=category,
        coordinates=Coordinates(lat=ev_lat, lng=ev_lng),
        sector=sec_name,
        severity=severity,
        casualty_count=1,
        summary=f"DTMF 2G Keypress {digits} emergency call received from {From}: {desc}.",
        confidence=0.85,
        source="voice",
        raw_transcript=f"[DTMF Keypress {digits} - {desc}]",
        verified=True,
        location_unknown=is_loc_unknown
    )

    final_event, _ = run_agentic_pipeline(event_payload)
    await ws_manager.broadcast_event(final_event.model_dump())

    return Response(content=str(response), media_type="application/xml")

@router.post("/process-audio")
async def voice_process_audio(
    RecordingUrl: Optional[str] = Form(None),
    RecordingSid: Optional[str] = Form(None),
    From: Optional[str] = Form("+919999111222"),
    lat: Optional[float] = Form(None),
    lng: Optional[float] = Form(None),
    sector: Optional[str] = Form(None)
):
    """
    FR-1.2 & FR-1.3:
    Processes voice recording:
    1. Downloads audio from Twilio / local storage
    2. Runs Whisper STT (without dummy text fabrication on silence/corruption)
    3. Runs entity extraction
    4. Runs Agentic Dispatcher (dedup, urgency, routing)
    5. Pushes Section 4.5 payload to WebSocket
    """
    response = VoiceResponse()
    response.say("Emergency report captured. Rescue dispatch units have been notified.", voice="Polly.Joanna")

    temp_audio_path = str(AUDIO_UPLOAD_DIR / f"{RecordingSid or uuid.uuid4().hex[:8]}.wav")

    # Download from Twilio if remote URL provided
    if RecordingUrl:
        try:
            r = requests.get(f"{RecordingUrl}.wav", timeout=6)
            if r.status_code == 200:
                with open(temp_audio_path, "wb") as f:
                    f.write(r.content)
        except Exception as e:
            print(f"[VOICE] Error fetching Twilio recording: {e}")

    # Process through AI pipeline (if file missing or corrupt, returns MANUAL_REVIEW with 0.3 conf)
    extracted = process_audio_transcript(temp_audio_path)

    # Resolve coordinates via sector hint or jitter
    sector_candidate = sector or extracted.get("sector_hint")
    ev_lat, ev_lng, sec_name, is_loc_unknown = resolve_voice_coordinates(
        lat=lat,
        lng=lng,
        sector_input=sector_candidate
    )

    # Construct Section 4.5 payload derived directly from extraction
    event_payload = EventPayload(
        category=extracted.get("category", "UNKNOWN"),
        coordinates=Coordinates(lat=ev_lat, lng=ev_lng),
        sector=sec_name,
        severity=extracted.get("severity", 5),
        casualty_count=extracted.get("casualty_count", 0),
        summary=extracted.get("summary", "Unintelligible audio, operator review required"),
        confidence=extracted.get("confidence", 0.3),
        source="voice",
        raw_transcript=extracted.get("raw_transcript"),
        verified=extracted.get("verified", False),
        status=extracted.get("status", "MANUAL_REVIEW"),
        location_unknown=is_loc_unknown
    )

    final_event, _ = run_agentic_pipeline(event_payload)
    await ws_manager.broadcast_event(final_event.model_dump())

    return Response(content=str(response), media_type="application/xml")
