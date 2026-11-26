"""
Simulation & Offline Fail-Safe Routes (Section 8 Risk Mitigations & Phase 5)
Provides:
- /api/simulate/voice: Feeds audio or pre-recorded disaster scenarios into pipeline if Twilio/Cloud is offline
- /api/simulate/scenario/{scenario_name}: Instant trigger for the 3 demo scenarios (Flood, Medical Emergency, Fire)
- /api/simulate/reset: Clears events and resets demo state
"""

from fastapi import APIRouter, UploadFile, File, Form, Depends
from starlette.concurrency import run_in_threadpool
import os
import wave
import struct
import math
import uuid
from typing import Optional

from ..config import AUDIO_SAMPLES_DIR, DEFAULT_CENTER_LAT, DEFAULT_CENTER_LNG
from ..schemas import EventPayload, Coordinates
from ..ai_engine import process_audio_transcript, offline_heuristic_nlp_extractor
from ..agentic_dispatcher import run_agentic_pipeline
from ..websocket_manager import ws_manager
from ..store import store
from ..security import verify_operator

router = APIRouter(prefix="/api/simulate", tags=["Offline Simulation & Scenarios"])

# Predefined Demo Scenarios
SCENARIOS = {
    "flood": {
        "text": "Flood waters have broken through the river barrier in Sector 18. Water is rising fast, at least 4 people are trapped on the rooftop of building 12. Send rescue boats immediately!",
        "category": "FLOOD",
        "severity": 9,
        "casualty_count": 4,
        "sector": "Sector 18 River Basin",
        "lat_offset": 0.006,
        "lng_offset": -0.007
    },
    "medical": {
        "text": "Emergency at the municipal market. An elderly citizen collapsed with severe cardiac distress and breathing difficulty. Please send an ambulance with oxygen right away, one person critical!",
        "category": "AMBULANCE",
        "severity": 8,
        "casualty_count": 1,
        "sector": "Central Municipal Market",
        "lat_offset": -0.005,
        "lng_offset": 0.008
    },
    "fire": {
        "text": "Massive fire broke out in the commercial warehouse complex in Industrial Sector 7. Dense black smoke, flames spreading to neighboring shops, 3 people trapped inside! Need fire tenders immediately!",
        "category": "FIRE",
        "severity": 9,
        "casualty_count": 3,
        "sector": "Industrial Sector 7",
        "lat_offset": 0.011,
        "lng_offset": 0.010
    }
}

def generate_synthetic_pcm_wav(file_path: str, duration_sec: float = 2.0, freq: float = 440.0):
    """Generates a valid 16kHz mono PCM WAV file for local STT audio pipelines."""
    sample_rate = 16000
    total_samples = int(sample_rate * duration_sec)
    with wave.open(file_path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        frames = bytearray()
        for i in range(total_samples):
            mod_freq = freq + 50.0 * math.sin(2 * math.pi * 5 * (i / sample_rate))
            value = int(10000.0 * math.sin(2 * math.pi * mod_freq * (i / sample_rate)))
            frames.extend(struct.pack('<h', value))
        wf.writeframes(frames)

@router.post("/voice")
async def simulate_voice(
    audio: Optional[UploadFile] = File(None),
    transcript_text: Optional[str] = Form(None),
    scenario: Optional[str] = Form(None)
):
    """
    Risk-2 Mitigation: Audio File Simulation Endpoint.
    Feeds pre-recorded voice clips or disaster transcript directly into the processing pipeline.
    """
    sample_path = str(AUDIO_SAMPLES_DIR / f"sim_{uuid.uuid4().hex[:6]}.wav")

    # If audio file uploaded, save it
    if audio:
        with open(sample_path, "wb") as f:
            f.write(await audio.read())
        extracted = await run_in_threadpool(process_audio_transcript, sample_path)
    elif scenario and scenario.lower() in SCENARIOS:
        sc = SCENARIOS[scenario.lower()]
        await run_in_threadpool(generate_synthetic_pcm_wav, sample_path)
        extracted = offline_heuristic_nlp_extractor(sc["text"])
        extracted["raw_transcript"] = sc["text"]
        extracted["category"] = sc["category"]
        extracted["severity"] = sc["severity"]
        extracted["casualty_count"] = sc["casualty_count"]
        extracted["confidence"] = 0.88
        extracted["verified"] = True
    elif transcript_text:
        await run_in_threadpool(generate_synthetic_pcm_wav, sample_path)
        extracted = offline_heuristic_nlp_extractor(transcript_text)
        extracted["raw_transcript"] = transcript_text
        extracted["confidence"] = 0.80
        extracted["verified"] = True
    else:
        sc = SCENARIOS["flood"]
        await run_in_threadpool(generate_synthetic_pcm_wav, sample_path)
        extracted = offline_heuristic_nlp_extractor(sc["text"])
        extracted["raw_transcript"] = sc["text"]
        extracted["category"] = sc["category"]
        extracted["severity"] = sc["severity"]
        extracted["casualty_count"] = sc["casualty_count"]
        extracted["confidence"] = 0.88
        extracted["verified"] = True

    category = extracted.get("category", "RESCUE")
    offset_map = {
        "FLOOD": (0.006, -0.007, "Sector 18 River Basin"),
        "AMBULANCE": (-0.005, 0.008, "Central Municipal Market"),
        "FIRE": (0.011, 0.010, "Industrial Sector 7"),
        "RESCUE": (0.003, -0.004, "Civic Infrastructure Zone")
    }
    lat_off, lng_off, default_sec = offset_map.get(category, (0.002, 0.002, "Central Sector"))

    event_payload = EventPayload(
        category=category,
        coordinates=Coordinates(
            lat=round(DEFAULT_CENTER_LAT + lat_off, 6),
            lng=round(DEFAULT_CENTER_LNG + lng_off, 6)
        ),
        sector=extracted.get("sector_hint", default_sec),
        severity=extracted.get("severity", 8),
        casualty_count=extracted.get("casualty_count", 1),
        summary=extracted.get("summary", "Simulated crisis report."),
        confidence=extracted.get("confidence", 0.85),
        source="voice",
        raw_transcript=extracted.get("raw_transcript"),
        verified=extracted.get("verified", True),
        status=extracted.get("status", "DISPATCHED")
    )

    final_event, state = run_agentic_pipeline(event_payload)
    await ws_manager.broadcast_event(final_event.model_dump())

    return {
        "status": "success",
        "simulation_mode": "offline_resilience",
        "event": final_event.model_dump(),
        "is_duplicate": state.is_duplicate,
        "agent_logs": state.action_log
    }

@router.post("/scenario/{scenario_name}")
async def trigger_scenario(scenario_name: str):
    """
    Phase 5 demo helper:
    Triggers one of the 3 specified demo disaster scenarios:
    - 'flood'
    - 'medical'
    - 'fire'
    """
    key = scenario_name.lower().strip()
    if key not in SCENARIOS:
        return {"error": f"Scenario '{scenario_name}' not found. Available: flood, medical, fire"}

    sc = SCENARIOS[key]
    event_payload = EventPayload(
        category=sc["category"],
        coordinates=Coordinates(
            lat=round(DEFAULT_CENTER_LAT + sc["lat_offset"], 6),
            lng=round(DEFAULT_CENTER_LNG + sc["lng_offset"], 6)
        ),
        sector=sc["sector"],
        severity=sc["severity"],
        casualty_count=sc["casualty_count"],
        summary=sc["text"],
        confidence=0.90,
        source="voice",
        raw_transcript=sc["text"],
        verified=True
    )

    final_event, state = run_agentic_pipeline(event_payload)
    await ws_manager.broadcast_event(final_event.model_dump())

    return {
        "status": "success",
        "scenario": key,
        "event": final_event.model_dump(),
        "is_duplicate": state.is_duplicate,
        "agent_logs": state.action_log
    }

@router.post("/reset", dependencies=[Depends(verify_operator)])
async def reset_store():
    """Resets event store and SQLite database to baseline state for fresh demo runs."""
    store.reset()
    return {"status": "reset_successful"}
