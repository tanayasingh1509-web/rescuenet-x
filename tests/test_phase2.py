"""
Unit and integration tests for Phase 2 Security features in RESCUENET-X.
Tests run synchronously with pure Python assertions to ensure 100% sandboxed execution.
"""

import os
import io
import time
from PIL import Image
from pydantic import ValidationError
from fastapi import HTTPException

from backend.config import ADMIN_TOKEN, ALLOWED_ORIGINS_LIST
from backend.security import (
    get_admin_token,
    ALLOWED_ENV_KEYS,
    secure_save_env_keys,
    is_safe_twilio_recording_url,
    validate_image_upload,
    validate_audio_upload,
    InMemoryRateLimiter
)

def test_admin_token_generation():
    """Verify admin token is non-empty, random, and securely loaded."""
    token = get_admin_token()
    assert token is not None and len(token) >= 32
    assert token == ADMIN_TOKEN

def test_env_key_whitelist_enforcement():
    """Verify secure_save_env_keys rejects disallowed keys and injections."""
    # 1. Allowed keys must succeed
    secure_save_env_keys({"GEMINI_MODEL": "gemini-1.5-flash"})
    assert os.environ.get("GEMINI_MODEL") == "gemini-1.5-flash"

    # 2. Dangerous / disallowed keys (e.g. OLLAMA_ENDPOINT, arbitrary shell variables) must be rejected
    rejected_forbidden = False
    try:
        secure_save_env_keys({"OLLAMA_ENDPOINT": "http://evil-server:11434/api/generate"})
    except HTTPException as e:
        rejected_forbidden = True
        assert e.status_code == 400
        assert "forbidden" in e.detail.lower()
    assert rejected_forbidden, "Expected HTTPException(400) when attempting to set OLLAMA_ENDPOINT"

    # 3. Newlines, CR, or NUL injections must be rejected
    rejected_injection = False
    try:
        secure_save_env_keys({"GEMINI_MODEL": "gemini-flash\nMALICIOUS_KEY=PWNED"})
    except HTTPException as e:
        rejected_injection = True
        assert e.status_code == 400
    assert rejected_injection, "Expected HTTPException(400) on newline injection"

def test_ssrf_twilio_recording_url():
    """Verify SSRF filter strictly accepts https://api.twilio.com and rejects attackers."""
    valid_url = "https://api.twilio.com/2010-04-01/Accounts/AC123/Recordings/RE456"
    assert is_safe_twilio_recording_url(valid_url) is True

    # Reject HTTP (must be HTTPS)
    assert is_safe_twilio_recording_url("http://api.twilio.com/recording.wav") is False

    # Reject external domains
    assert is_safe_twilio_recording_url("https://attacker.com/evil.wav") is False

    # Reject subdomain phishing
    assert is_safe_twilio_recording_url("https://api.twilio.com.attacker.com/recording.wav") is False
    assert is_safe_twilio_recording_url("https://attacker.com/api.twilio.com/test.wav") is False

    # Reject localhost / metadata endpoints
    assert is_safe_twilio_recording_url("https://169.254.169.254/latest/meta-data") is False
    assert is_safe_twilio_recording_url("https://localhost:8000/api/config/keys") is False

def test_file_upload_content_sniffing():
    """Verify real binary headers are validated and spoofed files are rejected."""
    # 1. Valid PNG
    img = Image.new("RGB", (100, 100), color="blue")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    png_bytes = buf.getvalue()
    ext = validate_image_upload(png_bytes)
    assert ext == ".png"

    # 2. Valid JPEG
    buf_jpg = io.BytesIO()
    img.save(buf_jpg, format="JPEG")
    jpg_bytes = buf_jpg.getvalue()
    ext_jpg = validate_image_upload(jpg_bytes)
    assert ext_jpg == ".jpg"

    # 3. HTML disguised as image must be rejected
    fake_img = b"<html><script>alert('xss')</script></html>"
    rejected_fake = False
    try:
        validate_image_upload(fake_img)
    except HTTPException as e:
        rejected_fake = True
        assert e.status_code == 400
    assert rejected_fake, "Expected HTTPException(400) when uploading HTML disguised as image"

    # 4. Exceeding max size (8MB) must be rejected
    oversized = b"A" * (8 * 1024 * 1024 + 1024)
    rejected_size = False
    try:
        validate_image_upload(oversized)
    except HTTPException as e:
        rejected_size = True
        assert e.status_code == 413
    assert rejected_size, "Expected HTTPException(413) when image exceeds 8MB"

def test_rate_limiter():
    """Verify in-memory sliding-window limiter blocks requests exceeding quota."""
    limiter = InMemoryRateLimiter(max_requests=5, window_seconds=2)
    test_ip = "192.168.1.100"

    # First 5 calls must pass
    for _ in range(5):
        limiter.check(test_ip)

    # 6th call must raise 429
    blocked = False
    try:
        limiter.check(test_ip)
    except HTTPException as e:
        blocked = True
        assert e.status_code == 429
    assert blocked, "Expected HTTPException(429) on exceeding rate limit"

def test_cors_configuration():
    """Verify CORS does not use wildcard origins with credentials."""
    assert "*" not in ALLOWED_ORIGINS_LIST
    assert any("localhost:5173" in orig for orig in ALLOWED_ORIGINS_LIST)
    assert any("localhost:8000" in orig for orig in ALLOWED_ORIGINS_LIST)

if __name__ == "__main__":
    print("[TEST 1] test_admin_token_generation...")
    test_admin_token_generation()
    print("[TEST 2] test_env_key_whitelist_enforcement...")
    test_env_key_whitelist_enforcement()
    print("[TEST 3] test_ssrf_twilio_recording_url...")
    test_ssrf_twilio_recording_url()
    print("[TEST 4] test_file_upload_content_sniffing...")
    test_file_upload_content_sniffing()
    print("[TEST 5] test_rate_limiter...")
    test_rate_limiter()
    print("[TEST 6] test_cors_configuration...")
    test_cors_configuration()
    print("========================================")
    print("ALL PHASE 2 SECURITY TESTS PASSED CLEANLY!")
    print("========================================")
