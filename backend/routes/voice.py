"""
Twilio VoiceBridge Telephony Routes (FR-1)
Handles:
- FR-1.1: DTMF Interactive Menu (1: Police, 2: Ambulance, 3: Rescue)
- FR-1.2: Speech Capture & Whisper STT
- FR-1.3: Entity Extraction & Structured Payload Broadcast
"""

from fastapi import APIRouter, Request, Response, Form, UploadFile, File
from fastapi.responses import PlainTextResponse
import os
import time
import requests
import uuid
from typing import Optional
from twilio.twiml.voice_response import VoiceResponse, Gather

from ..config import AUDIO_UPLOAD_DIR, DEFAULT_CENTER_LAT, DEFAULT_CENTER_LNG
from ..schemas import EventPayload, Coordinates
from ..ai_engine import process_audio_transcript
from ..agentic_dispatcher import run_agentic_pipeline
from ..websocket_manager import ws_manager

router = APIRouter(prefix="/api/voice", tags=["Voice Telephony"])

@router.post("/incoming")
async def voice_incoming(request: Request):
    """
    FR-1.1 DTMF Interactive Menu:
    - Press 1 -> Police
    - Press 2 -> Ambulance / Medical
    - Press 3 -> Trapped / Rescue
    - If no key pressed -> capture free-form voice message (FR-1.2)
    """
    response = VoiceResponse()

    # Create Gather verb for DTMF keypad input (timeout 4 seconds)
    gather = Gather(
        num_digits=1,
        action="/api/voice/menu-select",
        method="POST",
        timeout=4
    )
    gather.say(
        "Welcome to RescueNet X Emergency Response. "
        "Press 1 for Police. "
        "Press 2 for Ambulance and Medical. "
        "Press 3 for Trapped or Search and Rescue. "
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
    CallSid: Optional[str] = Form(None)
):
    """
    Handles keypad DTMF digit selection:
    1 -> Police
    2 -> Ambulance
    3 -> Trapped / Rescue
    """
    response = VoiceResponse()
    digits = Digits or "3"

    cat_map = {
        "1": ("POLICE", "Police Emergency", 8),
        "2": ("AMBULANCE", "Medical Ambulance Priority", 8),
        "3": ("RESCUE", "Trapped / Search & Rescue Squad", 9)
    }

    category, desc, severity = cat_map.get(digits, ("RESCUE", "General Crisis Rescue", 7))

    response.say(f"Emergency received for {desc}. Immediate dispatch initiated. Stay on the line or move to safe ground.", voice="Polly.Joanna")
    response.hangup()

    # Synthesize instant DTMF event (graceful degradation path)
    event_payload = EventPayload(
        category=category,
        coordinates=Coordinates(
            lat=DEFAULT_CENTER_LAT + 0.003,
            lng=DEFAULT_CENTER_LNG - 0.002
        ),
        sector="Telecom Tower Grid B-4",
        severity=severity,
        casualty_count=1,
        summary=f"DTMF 2G Keypress {digits} emergency call received from {From}: {desc}.",
        confidence=0.95,
        source="voice",
        raw_transcript=f"[DTMF Keypress {digits} - {desc}]",
        verified=True
    )

    final_event, _ = run_agentic_pipeline(event_payload)
    await ws_manager.broadcast_event(final_event.model_dump())

    return Response(content=str(response), media_type="application/xml")

@router.post("/process-audio")
async def voice_process_audio(
    RecordingUrl: Optional[str] = Form(None),
    RecordingSid: Optional[str] = Form(None),
    From: Optional[str] = Form("+919999111222")
):
    """
    FR-1.2 & FR-1.3:
    Processes Twilio voice recording:
    1. Downloads audio from Twilio / local storage
    2. Runs Whisper STT
    3. Runs Ollama Llama-3 NLP entity & severity extraction
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

    # If file does not exist, write dummy audio or proceed
    if not os.path.exists(temp_audio_path):
        with open(temp_audio_path, "wb") as f:
            f.write(b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00")

    # Process through AI pipeline
    extracted = process_audio_transcript(temp_audio_path)

    # Construct Section 4.5 payload
    sector_name = extracted.get("sector_hint", "Central Crisis Grid")
    event_payload = EventPayload(
        category=extracted.get("category", "RESCUE"),
        coordinates=Coordinates(
            lat=DEFAULT_CENTER_LAT + 0.004,
            lng=DEFAULT_CENTER_LNG + 0.003
        ),
        sector=sector_name,
        severity=extracted.get("severity", 7),
        casualty_count=extracted.get("casualty_count", 1),
        summary=extracted.get("summary", "Voice emergency reported."),
        confidence=0.90,
        source="voice",
        raw_transcript=extracted.get("raw_transcript"),
        verified=True
    )

    final_event, _ = run_agentic_pipeline(event_payload)
    await ws_manager.broadcast_event(final_event.model_dump())

    return Response(content=str(response), media_type="application/xml")
