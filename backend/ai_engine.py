"""
AI Engine for RESCUENET-X
Handles:
1. Speech-to-Text via OpenAI Whisper (auto-downgrading from base to tiny if pure inference latency > 1.5s)
2. NLP Entity & Severity Extraction via Google Gemini API or Ollama Llama-3 (with resilient offline fallback)
"""

import os
import json
import time
import re
import wave
import numpy as np
import requests
from typing import Optional, Dict, Any

from .config import OLLAMA_ENDPOINT, OLLAMA_MODEL, DEFAULT_WHISPER_MODEL, GEMINI_API_KEY, GEMINI_MODEL

# Guard Whisper import so the application boots gracefully if whisper is absent
try:
    import whisper
except ImportError:
    whisper = None
    print("[AI-ENGINE] OpenAI Whisper is not installed. Voice STT will run in fallback/manual-review mode.")

# Global model cache
current_model_name = DEFAULT_WHISPER_MODEL
stt_model = None

def get_whisper_model(model_name: str = "base"):
    """Lazy loader for whisper models."""
    global stt_model, current_model_name
    if whisper is None:
        return None
    if stt_model is None or current_model_name != model_name:
        print(f"[AI-ENGINE] Loading Whisper model: '{model_name}'...")
        try:
            stt_model = whisper.load_model(model_name)
            current_model_name = model_name
            print(f"[AI-ENGINE] Whisper '{model_name}' loaded successfully.")
        except Exception as e:
            print(f"[AI-ENGINE] Failed to load Whisper model '{model_name}': {e}")
            stt_model = None
    return stt_model

def extract_with_gemini(raw_text: str, api_key: str) -> Optional[dict]:
    """
    Extracts structured disaster crisis data using Google Gemini API.
    Sends API key in x-goog-api-key header (NOT in URL). Fails soft with logged reason.
    """
    if not api_key:
        return None

    active_model = os.getenv("GEMINI_MODEL", GEMINI_MODEL)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{active_model}:generateContent"
    headers = {
        "x-goog-api-key": api_key,
        "Content-Type": "application/json"
    }

    system_instruction = (
        "You are an emergency disaster response parser. Analyze the text and return valid JSON with: "
        'category (one of "POLICE", "AMBULANCE", "RESCUE", "FLOOD", "FIRE", "UNKNOWN"), '
        "severity (integer 1 to 10 based on threat to human life), "
        "casualty_count (integer estimated casualties or trapped people), "
        "sector_hint (short string indicating landmark, sector, or location if mentioned, else null), "
        "summary (1-sentence concise tactical emergency briefing)."
    )

    payload = {
        "contents": [{"parts": [{"text": f"Emergency crisis transcript: \"{raw_text}\""}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.1
        },
        "systemInstruction": {"parts": [{"text": system_instruction}]}
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=6)
        if response.status_code == 200:
            data = response.json()
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    text = parts[0].get("text", "{}")
                    parsed = json.loads(text)
                    if isinstance(parsed, dict) and "category" in parsed:
                        return parsed
        else:
            print(f"[AI-ENGINE] Gemini API returned error ({response.status_code}): {response.text}")
    except Exception as e:
        print(f"[AI-ENGINE] Gemini extraction failed soft: {e}")

    return None

def load_wav_pcm_fallback(audio_file_path: str):
    """
    Fallback reader for 16kHz mono WAV using standard Python wave + numpy,
    bypassing external ffmpeg if ffmpeg is unavailable on the host.
    """
    try:
        with wave.open(audio_file_path, 'rb') as wf:
            n_channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            framerate = wf.getframerate()
            n_frames = wf.getnframes()
            if n_frames == 0:
                return None
            raw_bytes = wf.readframes(n_frames)
            if not raw_bytes:
                return None

            if sampwidth == 2:
                dtype = np.int16
            elif sampwidth == 4:
                dtype = np.int32
            else:
                dtype = np.uint8

            audio_data = np.frombuffer(raw_bytes, dtype=dtype).astype(np.float32)

            # Convert to mono if multi-channel
            if n_channels > 1:
                audio_data = audio_data.reshape(-1, n_channels).mean(axis=1)

            # Normalize to [-1.0, 1.0]
            if sampwidth == 2:
                audio_data /= 32768.0
            elif sampwidth == 4:
                audio_data /= 2147483648.0

            # If sample rate differs from 16kHz, linear resample
            if framerate != 16000 and len(audio_data) > 0:
                indices = np.linspace(0, len(audio_data) - 1, int(len(audio_data) * 16000 / framerate))
                audio_data = np.interp(indices, np.arange(len(audio_data)), audio_data)

            # Check if audio is completely silent
            if np.max(np.abs(audio_data)) < 1e-4:
                return None

            return audio_data
    except Exception as e:
        print(f"[AI-ENGINE] WAV fallback reader error: {e}")
        return None

def offline_heuristic_nlp_extractor(raw_text: str) -> dict:
    """
    Offline resilient heuristic extractor used if LLMs are unreachable.
    Extracts signals from disaster speech text.
    """
    text_lower = raw_text.lower()

    # Determine category
    category = "UNKNOWN"
    if any(k in text_lower for k in ["fire", "flames", "smoke", "burning", "blaze", "gas leak"]):
        category = "FIRE"
    elif any(k in text_lower for k in ["flood", "water", "drown", "submerged", "river", "overflow"]):
        category = "FLOOD"
    elif any(k in text_lower for k in ["heart", "cardiac", "stroke", "bleeding", "ambulance", "doctor", "unconscious", "hospital"]):
        category = "AMBULANCE"
    elif any(k in text_lower for k in ["robbery", "thief", "gun", "police", "attack", "violence", "riot"]):
        category = "POLICE"
    elif any(k in text_lower for k in ["collapse", "trapped", "rubble", "earthquake", "stuck", "rescue"]):
        category = "RESCUE"
    else:
        category = "RESCUE"  # General emergency default

    # Extract casualty count
    casualty_count = 1
    num_words = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10
    }
    num_match = re.search(r'(\d+)\s*(people|persons|citizens|victims|casualties|trapped|injured)', text_lower)
    if num_match:
        casualty_count = int(num_match.group(1))
    else:
        for word, val in num_words.items():
            if f"{word} people" in text_lower or f"{word} trapped" in text_lower or f"{word} injured" in text_lower:
                casualty_count = val
                break

    # Determine severity (1-10)
    severity = 7
    if casualty_count > 5 or "critical" in text_lower or "deadly" in text_lower or "massive" in text_lower:
        severity = 9
    elif casualty_count > 2 or "trapped" in text_lower or "severe" in text_lower:
        severity = 8
    elif "urgent" in text_lower or "danger" in text_lower:
        severity = 7
    else:
        severity = 6

    # Extract sector / location hint if mentioned
    sector_match = re.search(r'(sector\s*\d+|block\s*[a-z0-9]+|near\s+[a-z0-9\s]+|bridge|highway|hospital|market|river)', text_lower)
    sector_hint = sector_match.group(0).title() if sector_match else "Central Disaster Sector"

    summary = f"{category} crisis reported near {sector_hint}: approx {casualty_count} person(s) at risk. {raw_text[:120]}".strip()

    return {
        "category": category,
        "severity": severity,
        "casualty_count": casualty_count,
        "summary": summary,
        "sector_hint": sector_hint
    }

def process_audio_transcript(audio_file_path: str) -> dict:
    """
    Transcribes audio file using Whisper and extracts structured crisis data.
    Strict rules:
    - Never fabricates a transcript when audio is silent, corrupt, or missing.
    - If STT fails, returns status MANUAL_REVIEW, confidence 0.3, verified=False, summary 'Unintelligible audio, operator review required'.
    - Times whisper STT inference exclusively without model loading time.
    """
    global current_model_name

    # 1. Validate file presence and non-zero content
    if not os.path.exists(audio_file_path) or os.path.getsize(audio_file_path) < 100:
        print("[AI-ENGINE] Audio file is missing, empty, or corrupt (<100 bytes).")
        return {
            "category": "UNKNOWN",
            "severity": 5,
            "casualty_count": 0,
            "summary": "Unintelligible audio, operator review required",
            "sector_hint": "Sector-Unknown",
            "raw_transcript": None,
            "confidence": 0.3,
            "verified": False,
            "status": "MANUAL_REVIEW",
            "stt_failed": True,
            "stt_latency_ms": 0
        }

    raw_text = ""
    stt_duration = 0.0

    # 2. Transcribe speech via Whisper
    try:
        model = get_whisper_model(current_model_name)
        if model is not None:
            # Time purely inference, NOT model loading
            t0 = time.time()
            try:
                transcription_result = model.transcribe(audio_file_path, fp16=False)
                raw_text = transcription_result.get("text", "").strip()
            except Exception as whisper_err:
                print(f"[AI-ENGINE] Whisper standard transcribe error: {whisper_err}. Trying PCM fallback...")
                pcm_audio = load_wav_pcm_fallback(audio_file_path)
                if pcm_audio is not None and len(pcm_audio) > 0:
                    transcription_result = model.transcribe(pcm_audio, fp16=False)
                    raw_text = transcription_result.get("text", "").strip()

            stt_duration = time.time() - t0
            print(f"[AI-ENGINE] STT inference completed in {stt_duration:.2f}s using '{current_model_name}': \"{raw_text}\"")

            # Auto-downgrade to whisper-tiny if inference exceeds 1.5s
            if stt_duration > 1.5 and current_model_name != "tiny":
                print(f"[AI-ENGINE] STT inference ({stt_duration:.2f}s) exceeded 1.5s budget. Downgrading Whisper model to 'tiny'.")
                try:
                    get_whisper_model("tiny")
                except Exception as e:
                    print(f"[AI-ENGINE] Failed to downgrade Whisper model to tiny: {e}")
        else:
            print("[AI-ENGINE] Whisper model unavailable.")
    except Exception as e:
        print(f"[AI-ENGINE] STT processing error: {e}")

    # 3. Check for silent / failed STT
    if not raw_text or len(raw_text.strip()) == 0:
        print("[AI-ENGINE] No speech detected or STT returned empty. Marking for MANUAL_REVIEW.")
        return {
            "category": "UNKNOWN",
            "severity": 5,
            "casualty_count": 0,
            "summary": "Unintelligible audio, operator review required",
            "sector_hint": "Sector-Unknown",
            "raw_transcript": None,
            "confidence": 0.3,
            "verified": False,
            "status": "MANUAL_REVIEW",
            "stt_failed": True,
            "stt_latency_ms": int(stt_duration * 1000)
        }

    # 4. Extract structured crisis entities
    parsed_json = None
    extraction_source = "heuristic"

    # Tier 1: Google Gemini API (if GEMINI_API_KEY is configured)
    active_gemini_key = os.getenv("GEMINI_API_KEY") or GEMINI_API_KEY
    if active_gemini_key:
        parsed_json = extract_with_gemini(raw_text, active_gemini_key)
        if parsed_json:
            extraction_source = "gemini"

    # Tier 2: Ollama Local Llama-3 (if Gemini was not used or failed)
    if not parsed_json or not isinstance(parsed_json, dict) or "category" not in parsed_json:
        prompt = f"""SYSTEM PROMPT:
You are a crisis intelligence parser. Analyze the given disaster transcript and return ONLY a JSON object with:
- "category": Choose from ["POLICE", "AMBULANCE", "RESCUE", "FLOOD", "FIRE", "UNKNOWN"]
- "severity": Integer from 1 to 10 based on threat to human life.
- "casualty_count": Estimated number of injured/trapped people (Integer).
- "summary": A 1-sentence tactical summary.

TRANSCRIPT: "{raw_text}"
"""
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "format": "json"
        }
        try:
            response = requests.post(OLLAMA_ENDPOINT, json=payload, timeout=4)
            if response.status_code == 200:
                resp_content = response.json().get("response", "{}")
                candidate = json.loads(resp_content)
                if isinstance(candidate, dict) and "category" in candidate:
                    parsed_json = candidate
                    extraction_source = "ollama"
        except Exception as e:
            print(f"[AI-ENGINE] Ollama unreachable ({e}). Using offline heuristic.")

    # Tier 3: Resilient offline heuristic
    if not parsed_json or not isinstance(parsed_json, dict) or "category" not in parsed_json:
        parsed_json = offline_heuristic_nlp_extractor(raw_text)
        extraction_source = "heuristic"

    # 5. Clean, validate, and compute derived confidence and verified status
    cat = parsed_json.get("category", "UNKNOWN").upper()
    valid_categories = {"POLICE", "AMBULANCE", "RESCUE", "FLOOD", "FIRE", "UNKNOWN"}
    if cat not in valid_categories:
        cat = "UNKNOWN"

    try:
        sev = max(1, min(10, int(parsed_json.get("severity", 7))))
    except Exception:
        sev = 7

    try:
        cas = max(0, int(parsed_json.get("casualty_count", 0)))
    except Exception:
        cas = 0

    # Derive confidence and verified status from actual extraction fidelity
    if extraction_source == "gemini":
        confidence = 0.88
        verified = True
        status = "DISPATCHED"
    elif extraction_source == "ollama":
        confidence = 0.82
        verified = True
        status = "DISPATCHED"
    else:
        # Heuristic extraction
        confidence = 0.75 if cat != "UNKNOWN" else 0.40
        verified = False
        status = "MANUAL_REVIEW" if confidence < 0.70 else "DISPATCHED"

    summary = parsed_json.get("summary") or f"{cat} incident reported from voice transmission."

    return {
        "category": cat,
        "severity": sev,
        "casualty_count": cas,
        "summary": summary,
        "sector_hint": parsed_json.get("sector_hint", "Central Crisis Grid"),
        "raw_transcript": raw_text,
        "confidence": confidence,
        "verified": verified,
        "status": status,
        "stt_failed": False,
        "stt_latency_ms": int(stt_duration * 1000)
    }
