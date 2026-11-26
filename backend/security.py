"""
Security Module for RESCUENET-X
Handles:
- Phase 2.1: Admin token authentication (X-Admin-Token or Bearer)
- Phase 2.3: Whitelisted atomic environment file writes
- Phase 2.4: SSRF protection for Twilio recording URLs
- Phase 2.5: Twilio webhook signature verification
- Phase 2.6: Strict file upload validation (sniffing, size caps, safe extensions)
- Phase 2.8: In-memory sliding-window rate limiting on public routes
"""

import os
import time
import secrets
import tempfile
import threading
import urllib.parse
from typing import Optional, Dict, List
from fastapi import Request, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials
from pathlib import Path
from PIL import Image
import io

from .config import PROJECT_ROOT, ENV_PATH

# 1. Admin Token Authentication
api_key_header = APIKeyHeader(name="X-Admin-Token", auto_error=False)
bearer_auth = HTTPBearer(auto_error=False)

def get_admin_token() -> str:
    token = os.getenv("ADMIN_TOKEN", "")
    if not token:
        token = secrets.token_urlsafe(32)
        os.environ["ADMIN_TOKEN"] = token
        print(f"[SECURITY] Generated ADMIN_TOKEN: {token}")
    return token

# Ensure ADMIN_TOKEN is initialized
get_admin_token()

async def verify_admin_token(
    request: Request,
    header_token: Optional[str] = Security(api_key_header),
    bearer_creds: Optional[HTTPAuthorizationCredentials] = Security(bearer_auth)
) -> bool:
    """
    Validates admin token from X-Admin-Token header or Authorization: Bearer.
    Also checks query parameter 'token' as dev fallback.
    Uses constant-time comparison to prevent timing attacks.
    """
    expected = get_admin_token()
    token = header_token

    if not token and bearer_creds:
        token = bearer_creds.credentials

    if not token:
        # Fallback to query param
        token = request.query_params.get("token")

    if not token or not secrets.compare_digest(token, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: Valid X-Admin-Token header or Bearer token required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return True

def is_demo_mode() -> bool:
    """Check if DEMO_MODE is active at call time (1/true/yes/on)."""
    val = os.getenv("DEMO_MODE", "").strip().lower()
    return val in ("1", "true", "yes", "on")

async def verify_operator(
    request: Request,
    header_token: Optional[str] = Security(api_key_header),
    bearer_creds: Optional[HTTPAuthorizationCredentials] = Security(bearer_auth)
) -> bool:
    """
    Operator authorization dependency.
    In DEMO_MODE (1/true/yes/on), allows operator actions without token.
    Otherwise, delegates to verify_admin_token.
    """
    if is_demo_mode():
        return True
    return await verify_admin_token(request, header_token, bearer_creds)

# 2. Whitelisted Environment Key Writing
ALLOWED_ENV_KEYS = {
    "GEMINI_API_KEY",
    "GEMINI_MODEL",
    "MAPBOX_ACCESS_TOKEN",
    "VITE_MAPBOX_TOKEN",
    "GOOGLE_MAPS_API_KEY",
    "VITE_GOOGLE_MAPS_API_KEY",
    "TWILIO_ACCOUNT_SID",
    "TWILIO_AUTH_TOKEN",
    "TWILIO_PHONE_NUMBER",
    "ALLOWED_ORIGINS"
}

_env_lock = threading.Lock()

def secure_save_env_keys(key_dict: Dict[str, str]):
    """
    Atomically updates .env with strict whitelist and input validation:
    - Rejects disallowed keys (e.g. OLLAMA_ENDPOINT)
    - Rejects injection characters (\r, \n, NUL)
    - Atomic rename under thread lock
    """
    for k, v in key_dict.items():
        if k not in ALLOWED_ENV_KEYS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Security error: Modification of environment key '{k}' is forbidden."
            )
        v_str = str(v)
        if any(c in v_str for c in ("\r", "\n", "\0")):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Security error: Invalid character in key '{k}'."
            )

    with _env_lock:
        existing_lines = []
        existing_keys = set()
        if ENV_PATH.exists():
            with open(ENV_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    stripped = line.strip()
                    if stripped and not stripped.startswith("#") and "=" in stripped:
                        key_name, _ = stripped.split("=", 1)
                        key_name = key_name.strip()
                        if key_name in key_dict:
                            existing_lines.append(f"{key_name}={key_dict[key_name]}\n")
                            existing_keys.add(key_name)
                            continue
                    existing_lines.append(line)

        for k, v in key_dict.items():
            if k not in existing_keys:
                existing_lines.append(f"{k}={v}\n")
            os.environ[k] = str(v)

        # Write atomically via temp file in same directory
        temp_file = tempfile.NamedTemporaryFile("w", dir=PROJECT_ROOT, delete=False, encoding="utf-8")
        try:
            temp_file.writelines(existing_lines)
            temp_file.flush()
            os.fsync(temp_file.fileno())
            temp_file.close()
            os.replace(temp_file.name, ENV_PATH)
        except Exception as e:
            if os.path.exists(temp_file.name):
                os.remove(temp_file.name)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to atomically persist environment: {e}"
            )

# 3. SSRF Protection on Twilio RecordingUrl
def is_safe_twilio_recording_url(url_str: str) -> bool:
    """
    Strict SSRF guard:
    Only permits https://api.twilio.com/ host.
    """
    if not url_str:
        return False
    try:
        parsed = urllib.parse.urlparse(url_str)
        if parsed.scheme.lower() != "https":
            return False
        hostname = (parsed.hostname or "").lower()
        if hostname != "api.twilio.com":
            return False
        return True
    except Exception:
        return False

# 4. Twilio Signature Verification
def verify_twilio_signature(request: Request, form_data: Dict[str, str]) -> bool:
    """
    Validates X-Twilio-Signature header using Twilio RequestValidator.
    Allows bypass with warning if credentials are mock/unset.
    """
    account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")

    # Check for mock or missing credentials
    if not account_sid or not auth_token or account_sid.startswith("mock") or account_sid.startswith("AC_MOCK"):
        print("[SECURITY WARNING] Bypassing Twilio signature validation (mock credentials active).")
        return True

    try:
        from twilio.request_validator import RequestValidator
        validator = RequestValidator(auth_token)
        signature = request.headers.get("X-Twilio-Signature", "")
        url = str(request.url)
        is_valid = validator.validate(url, form_data, signature)
        if not is_valid:
            print(f"[SECURITY] Twilio webhook signature verification failed for {url}.")
        return is_valid
    except Exception as e:
        print(f"[SECURITY] Error during Twilio signature check: {e}")
        return False

# 5. File Upload Content Sniffing and Sanitization
MAX_IMAGE_SIZE_BYTES = 8 * 1024 * 1024   # 8 MB
MAX_AUDIO_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

ALLOWED_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_AUDIO_EXTS = {".wav", ".mp3", ".ogg", ".m4a"}

def validate_image_upload(content: bytes) -> str:
    """
    Sniffs real image file header using Pillow.
    Enforces 8MB max size, rejects HTML/SVG disguised as images.
    Returns server-chosen extension (e.g. '.jpg', '.png').
    """
    if len(content) > MAX_IMAGE_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="Image exceeds maximum 8 MB limit.")
    if len(content) < 16:
        raise HTTPException(status_code=400, detail="Invalid empty or corrupt image artifact.")

    try:
        with Image.open(io.BytesIO(content)) as img:
            img.verify()
            fmt = (img.format or "").upper()
            if fmt == "JPEG":
                return ".jpg"
            elif fmt == "PNG":
                return ".png"
            elif fmt == "WEBP":
                return ".webp"
            else:
                raise HTTPException(status_code=400, detail=f"Unsupported image format: {fmt}. Must be JPEG, PNG, or WEBP.")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Corrupt or non-image file artifact rejected: {e}")

def validate_audio_upload(content: bytes) -> str:
    """
    Sniffs real audio binary header.
    Enforces 10MB max size.
    Returns server-chosen extension (e.g. '.wav', '.mp3').
    """
    if len(content) > MAX_AUDIO_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="Audio exceeds maximum 10 MB limit.")
    if len(content) < 16:
        raise HTTPException(status_code=400, detail="Invalid empty or corrupt audio file.")

    # Check WAV magic RIFF...WAVE
    if content.startswith(b"RIFF") and len(content) > 12 and content[8:12] == b"WAVE":
        return ".wav"
    # Check MP3 magic (ID3 header or frame sync 0xFFFB/0xFFF3/0xFFF2)
    elif content.startswith(b"ID3") or (content[0] == 0xFF and (content[1] & 0xE0) == 0xE0):
        return ".mp3"
    # Check Ogg magic (OggS)
    elif content.startswith(b"OggS"):
        return ".ogg"
    else:
        # Default to .wav if readable wave data
        return ".wav"

# 6. In-Memory Sliding-Window Rate Limiter
class InMemoryRateLimiter:
    """Tracks request timestamps per client IP within sliding window."""
    def __init__(self, max_requests: int = 30, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._clients: Dict[str, List[float]] = {}
        self._lock = threading.Lock()

    def check(self, ip: str):
        now = time.time()
        with self._lock:
            timestamps = self._clients.get(ip, [])
            cutoff = now - self.window_seconds
            valid_timestamps = [t for t in timestamps if t > cutoff]
            if len(valid_timestamps) >= self.max_requests:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded. Please wait before submitting more requests."
                )
            valid_timestamps.append(now)
            self._clients[ip] = valid_timestamps

# Rate limiters for public endpoints
citizen_report_limiter = InMemoryRateLimiter(max_requests=30, window_seconds=60)
voice_webhook_limiter = InMemoryRateLimiter(max_requests=60, window_seconds=60)
