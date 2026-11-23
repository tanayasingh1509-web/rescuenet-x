"""
Configuration settings for RESCUENET-X backend.
Supports automatic .env loading for Google Gemini, Mapbox, and Twilio credentials.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
ENV_PATH = PROJECT_ROOT / ".env"

def load_env_file():
    """Lightweight zero-dependency .env loader."""
    if ENV_PATH.exists():
        try:
            with open(ENV_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, val = line.split("=", 1)
                        key = key.strip()
                        val = val.strip().strip('"').strip("'")
                        if key:
                            os.environ[key] = val
        except Exception as e:
            print(f"[CONFIG] Error reading .env: {e}")

# Load environment variables on startup
load_env_file()

def save_env_keys(key_dict: dict):
    """Safely writes or updates environment keys in .env and os.environ."""
    existing_lines = []
    existing_keys = set()
    if ENV_PATH.exists():
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped and not stripped.startswith("#") and "=" in stripped:
                    k, _ = stripped.split("=", 1)
                    k = k.strip()
                    if k in key_dict:
                        existing_lines.append(f"{k}={key_dict[k]}\n")
                        existing_keys.add(k)
                        continue
                existing_lines.append(line)

    for k, v in key_dict.items():
        if k not in existing_keys:
            existing_lines.append(f"{k}={v}\n")
        os.environ[k] = str(v)

    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.writelines(existing_lines)

# Google Gemini API Configuration (for high-accuracy cloud LLM entity & severity extraction)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

# Ollama & Whisper configuration (local fallback)
OLLAMA_ENDPOINT = os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
DEFAULT_WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")

# Storage paths
AUDIO_UPLOAD_DIR = BASE_DIR / "uploads" / "audio"
IMAGE_UPLOAD_DIR = BASE_DIR / "uploads" / "images"
AUDIO_SAMPLES_DIR = BASE_DIR / "audio_samples"

AUDIO_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
IMAGE_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
AUDIO_SAMPLES_DIR.mkdir(parents=True, exist_ok=True)

# Mapbox Access Token (for vector GIS mapping)
MAPBOX_ACCESS_TOKEN = os.getenv("MAPBOX_ACCESS_TOKEN", os.getenv("VITE_MAPBOX_TOKEN", ""))

# Google Maps API Key (for high-fidelity GIS tactical satellite & vector mapping)
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", os.getenv("VITE_GOOGLE_MAPS_API_KEY", ""))

# Twilio configuration (for live webhooks via Ngrok or local testing)
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "")

# Server configuration
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
DEBUG = os.getenv("DEBUG", "True").lower() == "true"

# Default City Center for demo GIS (e.g. National Capital Region / Flood-prone river basin)
DEFAULT_CENTER_LAT = 28.6139
DEFAULT_CENTER_LNG = 77.2090
