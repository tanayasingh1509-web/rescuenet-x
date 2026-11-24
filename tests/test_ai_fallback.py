#!/usr/bin/env python3
"""
Test Suite: AI Fallback, Audio STT, and Vision Robustness
Verifies:
1. Silent audio produces status="MANUAL_REVIEW", confidence=0.3, verified=False
2. Color heuristic alone caps confidence at <= 0.80 and NEVER marks verified=True
3. Collapse image is NOT misclassified as flood
4. Gemini fail-soft works when external API returns 500/fails
"""

import sys
import io
import wave
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from PIL import Image

# Add project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.ai_engine import process_audio_transcript, extract_with_gemini
from backend.vision_engine import analyze_visual_disaster

def create_silent_wav() -> Path:
    """Generate a 2-second pure silence 16kHz mono WAV file."""
    temp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    temp_wav.close()
    with wave.open(temp_wav.name, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(b"\x00" * 32000) # 2 seconds of silence
    return Path(temp_wav.name)

def test_silent_audio_produces_manual_review():
    silent_wav = create_silent_wav()
    try:
        result = process_audio_transcript(str(silent_wav))

        assert result.get("status") == "MANUAL_REVIEW", f"Expected MANUAL_REVIEW, got {result.get('status')}"
        assert result.get("confidence") == 0.3, f"Expected confidence 0.3, got {result.get('confidence')}"
        assert result.get("verified") is False, "Silent audio must never be marked verified"
        assert "unintelligible audio" in result.get("summary", "").lower(), "Summary must indicate unintelligible audio"
    finally:
        silent_wav.unlink(missing_ok=True)

def test_color_heuristic_never_marks_verified():
    # Generate pure fire-orange test image
    img = Image.new("RGB", (640, 480), color=(255, 69, 0))
    temp_img = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    temp_img.close()
    img.save(temp_img.name)

    try:
        # Run vision engine with no Gemini key
        with patch.dict("os.environ", {"GEMINI_API_KEY": ""}):
            result = analyze_visual_disaster(temp_img.name)

            # Heuristic alone must NEVER exceed 0.80 confidence and NEVER mark verified
            assert result["confidence"] <= 0.80, f"Confidence {result['confidence']} exceeded 0.80 cap for heuristic"
            assert result["verified"] is False, "Heuristic alone must NEVER mark verified=True"
            assert result["status"] == "MANUAL_REVIEW", f"Status must be MANUAL_REVIEW, got {result['status']}"
            assert "heuristic" in result["summary"].lower(), "Summary must explicitly declare heuristic analysis"
    finally:
        Path(temp_img.name).unlink(missing_ok=True)

def test_collapse_image_not_misclassified_as_flood():
    # Concrete/rubble grey image with high texture/Laplacian variance (gray: 128, 128, 128 with speckles)
    import numpy as np
    # High-variance desaturated concrete texture
    arr = np.random.randint(100, 160, (480, 640, 3), dtype=np.uint8)
    img = Image.fromarray(arr)
    temp_img = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    temp_img.close()
    img.save(temp_img.name)

    try:
        with patch.dict("os.environ", {"GEMINI_API_KEY": ""}):
            result = analyze_visual_disaster(temp_img.name)
            assert result["category"] != "FLOOD", f"Concrete/rubble texture must NOT be classified as FLOOD, got {result['category']}"
            assert result["category"] in ["RESCUE", "COLLAPSE"], f"Expected RESCUE/COLLAPSE, got {result['category']}"
    finally:
        Path(temp_img.name).unlink(missing_ok=True)

def test_gemini_fail_soft_on_error():
    # Mock requests.post to return HTTP 500
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.text = "Internal Server Error upstream"

    with patch("requests.post", return_value=mock_resp):
        # extract_with_gemini must fail soft and return None on HTTP 500
        result = extract_with_gemini("Major bridge collapsed near sector 18", api_key="test_key")
        assert result is None, "Failed: Gemini call must fail soft and return None on HTTP 500"

if __name__ == "__main__":
    print("Running AI Fallback & Vision Robustness Test Suite...")
    test_silent_audio_produces_manual_review()
    print("  ✓ Silent audio produces status=MANUAL_REVIEW and confidence=0.3")
    test_color_heuristic_never_marks_verified()
    print("  ✓ Color/edge heuristic confidence capped at 0.80 with verified=False")
    test_collapse_image_not_misclassified_as_flood()
    print("  ✓ Rubble/collapse image correctly identified as RESCUE, not FLOOD")
    test_gemini_fail_soft_on_error()
    print("  ✓ Gemini API failure fails soft without raising unhandled exception")
    print("✅ All AI fallback tests passed!")
