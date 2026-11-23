"""
Configuration settings for RESCUENET-X backend.
Supports automatic .env loading for Google Gemini, Mapbox, and Twilio credentials.
"""

import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
ENV_PATH = PROJECT_ROOT / ".env"

# Guard Ultralytics config directory inside project to prevent permission warnings
os.environ.setdefault("YOLO_CONFIG_DIR", str(PROJECT_ROOT / ".ultralytics"))

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

# Admin Token Initialization
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")
if not ADMIN_TOKEN:
    ADMIN_TOKEN = secrets.token_urlsafe(32)
    os.environ["ADMIN_TOKEN"] = ADMIN_TOKEN
    print(f"[SECURITY] Generated initial ADMIN_TOKEN: {ADMIN_TOKEN}")

# Allowed CORS Origins (no wildcard with credentials)
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000,http://localhost:8000,http://127.0.0.1:8000"
)
ALLOWED_ORIGINS_LIST = [orig.strip() for orig in ALLOWED_ORIGINS.split(",") if orig.strip()]

def save_env_keys(key_dict: dict):
    """Delegates to hardened atomic security writer."""
    from .security import secure_save_env_keys
    secure_save_env_keys(key_dict)

# Google Gemini API Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

# Ollama & Whisper configuration
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

# Mapbox Access Token
MAPBOX_ACCESS_TOKEN = os.getenv("MAPBOX_ACCESS_TOKEN", os.getenv("VITE_MAPBOX_TOKEN", ""))

# Google Maps API Key
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", os.getenv("VITE_GOOGLE_MAPS_API_KEY", ""))

# Twilio configuration
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "")

# Server configuration
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
DEBUG = os.getenv("DEBUG", "True").lower() == "true"

# Default City Center for demo GIS
DEFAULT_CENTER_LAT = 28.6139
DEFAULT_CENTER_LNG = 77.2090
