"""
Configuration & API Key Management Routes for RESCUENET-X
Allows operators to securely inspect, configure, and test API credentials.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import os
import requests

from ..config import (
    save_env_keys,
    GEMINI_API_KEY,
    GEMINI_MODEL,
    MAPBOX_ACCESS_TOKEN,
    TWILIO_ACCOUNT_SID,
    TWILIO_PHONE_NUMBER
)

router = APIRouter(prefix="/api/config", tags=["Configuration & Credentials"])

def mask_key(val: str) -> str:
    """Safely masks an API key (e.g. AIzaSy...94xQ) without exposing secrets."""
    if not val or val.startswith("AC_MOCK") or val.startswith("mock_"):
        return ""
    if len(val) <= 8:
        return "••••••••"
    return f"{val[:6]}••••••••{val[-4:]}"

class KeyConfigPayload(BaseModel):
    gemini_api_key: Optional[str] = None
    mapbox_token: Optional[str] = None
    google_maps_api_key: Optional[str] = None
    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    twilio_phone_number: Optional[str] = None

class GeminiTestPayload(BaseModel):
    api_key: Optional[str] = None

@router.get("/keys")
async def get_key_status():
    """Returns safe masked status of all configured API keys."""
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    mapbox_token = os.getenv("MAPBOX_ACCESS_TOKEN", os.getenv("VITE_MAPBOX_TOKEN", ""))
    google_maps_key = os.getenv("GOOGLE_MAPS_API_KEY", os.getenv("VITE_GOOGLE_MAPS_API_KEY", "AIzaSyAOVYRIgupAurZup5y1PRh8Ismb1A3lLao"))
    twilio_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
    twilio_num = os.getenv("TWILIO_PHONE_NUMBER", "")

    return {
        "gemini": {
            "configured": bool(gemini_key),
            "masked": mask_key(gemini_key),
            "model": os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        },
        "google_maps": {
            "configured": bool(google_maps_key),
            "masked": mask_key(google_maps_key),
            "raw_key": google_maps_key # safe client public key for Maps JS SDK
        },
        "mapbox": {
            "configured": bool(mapbox_token and not mapbox_token.startswith("pk.mock")),
            "masked": mask_key(mapbox_token)
        },
        "twilio": {
            "configured": bool(twilio_sid and not twilio_sid.startswith("AC_MOCK")),
            "masked_sid": mask_key(twilio_sid),
            "phone_number": twilio_num
        }
    }

@router.post("/keys")
async def update_keys(payload: KeyConfigPayload):
    """Safely updates and persists API keys to .env and active runtime."""
    updates = {}
    if payload.gemini_api_key is not None:
        updates["GEMINI_API_KEY"] = payload.gemini_api_key.strip()
    if payload.google_maps_api_key is not None:
        updates["GOOGLE_MAPS_API_KEY"] = payload.google_maps_api_key.strip()
        updates["VITE_GOOGLE_MAPS_API_KEY"] = payload.google_maps_api_key.strip()
    if payload.mapbox_token is not None:
        updates["MAPBOX_ACCESS_TOKEN"] = payload.mapbox_token.strip()
        updates["VITE_MAPBOX_TOKEN"] = payload.mapbox_token.strip()
    if payload.twilio_account_sid is not None:
        updates["TWILIO_ACCOUNT_SID"] = payload.twilio_account_sid.strip()
    if payload.twilio_auth_token is not None:
        updates["TWILIO_AUTH_TOKEN"] = payload.twilio_auth_token.strip()
    if payload.twilio_phone_number is not None:
        updates["TWILIO_PHONE_NUMBER"] = payload.twilio_phone_number.strip()

    save_env_keys(updates)

    return {
        "status": "success",
        "updated_keys": list(updates.keys()),
        "message": f"Successfully updated {len(updates)} environment key(s)."
    }

@router.post("/test-gemini")
async def test_gemini_connection(payload: GeminiTestPayload):
    """Tests live connection to Google Gemini API."""
    key = payload.api_key or os.getenv("GEMINI_API_KEY", "")
    if not key:
        raise HTTPException(status_code=400, detail="No Gemini API key provided to test.")

    model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"

    test_body = {
        "contents": [{"parts": [{"text": "Hello, emergency test message."}]}]
    }

    try:
        res = requests.post(url, json=test_body, timeout=6)
        if res.status_code == 200:
            return {
                "status": "connected",
                "model": model,
                "message": "Successfully authenticated with Google Gemini API."
            }
        else:
            return {
                "status": "error",
                "code": res.status_code,
                "detail": res.text
            }
    except Exception as e:
        return {
            "status": "error",
            "detail": str(e)
        }
