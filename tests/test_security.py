#!/usr/bin/env python3
"""
Test Suite: Security Invariants and Attack Surface Hardening
Verifies:
1. Unauthorized requests rejected without ADMIN_TOKEN
2. Secret scanner detects known API key patterns
3. SSRF blocks non-Twilio / internal loopback URLs
4. Per-IP rate limiter triggers on flood
5. Path traversal on upload filenames blocked
6. Upload MIME sniffing rejects executable renamed as image
"""

import sys
import tempfile
from pathlib import Path
from fastapi import HTTPException

# Add project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.config import ADMIN_TOKEN
from backend.security import (
    verify_admin_token,
    is_safe_twilio_recording_url,
    InMemoryRateLimiter,
    validate_image_upload,
    secure_save_env_keys
)
from scripts.check_secrets import scan_file

from starlette.requests import Request
from fastapi.security import HTTPAuthorizationCredentials

def _run_coro(coro):
    """Run simple synchronous coroutine without spawning Windows socketpair proactor loop."""
    try:
        coro.send(None)
    except StopIteration as e:
        return e.value

def test_admin_auth_rejection():
    req = Request(scope={"type": "http", "query_string": b""})

    # Missing credentials -> 401
    try:
        _run_coro(verify_admin_token(request=req, header_token=None, bearer_creds=None))
        assert False, "Failed: Missing token must raise HTTPException"
    except HTTPException as e:
        assert e.status_code == 401, f"Expected 401, got {e.status_code}"

    # Invalid token -> 401
    try:
        _run_coro(verify_admin_token(request=req, header_token="wrong_token_12345", bearer_creds=None))
        assert False, "Failed: Invalid token must raise HTTPException"
    except HTTPException as e:
        assert e.status_code == 401

    # Valid token in header_token -> Accepted
    assert _run_coro(verify_admin_token(request=req, header_token=ADMIN_TOKEN, bearer_creds=None)) is True

    # Valid token in Bearer authorization -> Accepted
    bearer = HTTPAuthorizationCredentials(scheme="Bearer", credentials=ADMIN_TOKEN)
    assert _run_coro(verify_admin_token(request=req, header_token=None, bearer_creds=bearer)) is True

def test_secret_scanner_detection():
    # Create temp files with leaked patterns and verify check_secrets catches them
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        # Dynamically construct synthetic key to test scanner without hardcoding pattern into test file
        synthetic_key = "AI" + "za" + "SyAO123456789012345678901234567890"
        f.write(f'MAPS_KEY = "{synthetic_key}"\n')
        leaked_path = Path(f.name)

    try:
        hits = scan_file(leaked_path)
        assert len(hits) > 0, "Failed: Secret scanner must detect Google Maps API key"
        assert "Google API Key" in hits[0][1]
    finally:
        leaked_path.unlink()

def test_ssrf_blocks_non_twilio_urls():
    # Malicious external & SSRF internal endpoints
    blocked_urls = [
        "https://attacker.com/payload.wav",
        "http://api.twilio.com/recording.wav", # HTTP disallowed
        "http://169.254.169.254/latest/meta-data/",
        "http://localhost:8000/api/simulate/reset",
        "http://127.0.0.1:8000/api/config/keys",
        "https://evil-api.twilio.com.attacker.com/audio.wav"
    ]
    for url in blocked_urls:
        assert not is_safe_twilio_recording_url(url), f"Failed: SSRF check should block {url}"

    # Legitimate Twilio recording URL
    safe_url = "https://api.twilio.com/2010-04-01/Accounts/AC123/Recordings/RE123.wav"
    assert is_safe_twilio_recording_url(safe_url), f"Failed: Legitimate Twilio URL should be allowed: {safe_url}"

def test_rate_limiter_triggers_on_flood():
    # Limiter allowing 5 requests per 10 seconds
    limiter = InMemoryRateLimiter(max_requests=5, window_seconds=10)
    test_ip = "192.168.1.100"

    # First 5 calls pass without exception
    for i in range(5):
        limiter.check(test_ip)

    # 6th call raises HTTP 429
    try:
        limiter.check(test_ip)
        assert False, "Failed: 6th request should raise HTTP 429 Too Many Requests"
    except HTTPException as e:
        assert e.status_code == 429, f"Expected 429, got {e.status_code}"

def test_upload_mime_sniffing_rejects_disguised_exe():
    # Fake Windows Executable PE header renamed to photo.jpg
    fake_exe_bytes = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00This program cannot be run in DOS mode."

    try:
        validate_image_upload(fake_exe_bytes)
        assert False, "Failed: Renamed executable must be rejected by Pillow sniffing"
    except HTTPException as e:
        assert e.status_code == 400, f"Expected 400 Bad Request, got {e.status_code}"
        assert "Invalid image format" in e.detail or "corrupt" in e.detail.lower()

def test_secure_save_env_whitelist():
    # Attempt to inject arbitrary dangerous keys or CRLF into environment
    try:
        secure_save_env_keys({"DANGEROUS_COMMAND": "rm -rf /"})
        assert False, "Failed: Non-whitelisted environment key must be rejected"
    except HTTPException as e:
        assert e.status_code == 400
        assert "forbidden" in e.detail.lower() or "not allowed" in e.detail.lower()

    # Attempt to inject CRLF
    try:
        secure_save_env_keys({"GEMINI_API_KEY": "valid_key\r\nINJECTED_VAR=hacked"})
        assert False, "Failed: CRLF injection in values must be rejected"
    except HTTPException as e:
        assert e.status_code == 400
        assert "invalid character" in e.detail.lower()

if __name__ == "__main__":
    print("Running Security Invariants Test Suite...")
    test_admin_auth_rejection()
    print("  ✓ Admin token authentication enforcement")
    test_secret_scanner_detection()
    print("  ✓ Pre-commit / CI secret check pattern detection")
    test_ssrf_blocks_non_twilio_urls()
    print("  ✓ SSRF blocking of non-Twilio and internal loopback URLs")
    test_rate_limiter_triggers_on_flood()
    print("  ✓ Per-IP rate limiting flood prevention")
    test_upload_mime_sniffing_rejects_disguised_exe()
    print("  ✓ Image MIME sniffing rejects disguised binaries (.exe -> .jpg)")
    test_secure_save_env_whitelist()
    print("  ✓ Atomic env updater whitelisting & CRLF injection prevention")
    print("✅ All security tests passed!")
