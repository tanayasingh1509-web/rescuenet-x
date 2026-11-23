"""
Vision Verification Engine for RESCUENET-X
Handles:
1. Disaster Image Classification (Flood, Fire, Collapse) using:
   - Optional Google Gemini Vision classifier (when GEMINI_API_KEY is configured)
   - Weak color/edge/texture heuristic capped at 0.80 confidence (held for manual review)
   - YOLO11n / YOLOv8n object detection used solely for human/person counting (COCO has no fire/flood classes)
2. Two-Tier Confidence Logic (FR-2.1):
   - Heuristics: max 0.80 confidence, marked unverified, held for operator review (MANUAL_REVIEW)
   - Real classifier (Gemini Vision): allowed >= 0.85 confidence, marked verified
3. Perceptual Hashing (pHash) for Deduplication (FR-2.3)
"""

import os
import base64
import json
import cv2
import numpy as np
from PIL import Image
import imagehash
from typing import Dict, Any, Tuple, Optional
import requests

from .config import GEMINI_API_KEY, GEMINI_MODEL

# Configure Ultralytics cache directory inside project root to avoid host permission errors
os.environ.setdefault("YOLO_CONFIG_DIR", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".ultralytics")))

# Try loading YOLO model from ultralytics if available
yolo_model = None
try:
    from ultralytics import YOLO
    try:
        yolo_model = YOLO("yolo11n.pt")
        print("[VISION] Loaded YOLOv11 nano model for person counting.")
    except Exception:
        try:
            yolo_model = YOLO("yolov8n.pt")
            print("[VISION] Loaded YOLOv8 nano model for person counting.")
        except Exception as e:
            print(f"[VISION] YOLO weight auto-load deferred ({e}).")
            yolo_model = None
except Exception as e:
    print(f"[VISION] Ultralytics import error: {e}")

def compute_image_phash(image_path: str) -> str:
    """
    Computes 64-bit Perceptual Hash (pHash) using ImageHash library.
    """
    try:
        with Image.open(image_path) as img:
            h = imagehash.phash(img)
            return str(h)
    except Exception as e:
        print(f"[VISION] pHash computation error: {e}")
        return ""

def classify_with_gemini_vision(image_path: str, api_key: str) -> Optional[Dict[str, Any]]:
    """
    Calls Google Gemini multimodal vision model using x-goog-api-key header.
    Fails soft with logged reason.
    """
    if not api_key:
        return None

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    headers = {
        "x-goog-api-key": api_key,
        "Content-Type": "application/json"
    }

    try:
        with open(image_path, "rb") as f:
            img_bytes = f.read()
        b64_data = base64.b64encode(img_bytes).decode("utf-8")

        prompt = (
            "You are an emergency disaster image classification system. "
            "Analyze the image and return a JSON object with: "
            'category (one of "FLOOD", "FIRE", "RESCUE", "AMBULANCE", "POLICE", "UNKNOWN"), '
            "confidence (float 0.0 to 1.0 representing how clearly the disaster is visible), "
            "severity (integer 1 to 10 based on threat to human life and damage), "
            "person_count (integer number of visible people), "
            "summary (1-sentence concise description of the crisis)."
        )

        payload = {
            "contents": [{
                "parts": [
                    {
                        "inlineData": {
                            "mimeType": "image/jpeg",
                            "data": b64_data
                        }
                    },
                    {"text": prompt}
                ]
            }],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.1
            }
        }

        response = requests.post(url, headers=headers, json=payload, timeout=8)
        if response.status_code == 200:
            data = response.json()
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    result_text = parts[0].get("text", "{}")
                    parsed = json.loads(result_text)
                    cat = parsed.get("category", "UNKNOWN").upper()
                    if cat not in {"FLOOD", "FIRE", "RESCUE", "AMBULANCE", "POLICE", "UNKNOWN"}:
                        cat = "UNKNOWN"
                    conf = max(0.0, min(1.0, float(parsed.get("confidence", 0.85))))
                    sev = max(1, min(10, int(parsed.get("severity", 7))))
                    person_cnt = max(0, int(parsed.get("person_count", 0)))
                    summ = parsed.get("summary") or f"Gemini Vision verified {cat} disaster."
                    return {
                        "category": cat,
                        "confidence": conf,
                        "severity": sev,
                        "person_count": person_cnt,
                        "summary": f"Gemini Vision: {summ}"
                    }
        else:
            print(f"[VISION] Gemini Vision API error ({response.status_code}): {response.text}")
    except Exception as e:
        print(f"[VISION] Gemini Vision classification failed soft: {e}")

    return None

def count_people_yolo(image_path: str) -> int:
    """Uses YOLO (COCO) exclusively for person counting."""
    if yolo_model is None:
        return 0
    try:
        results = yolo_model(image_path, verbose=False)
        person_count = 0
        for r in results:
            for c in r.boxes.cls:
                label = r.names[int(c)]
                if label == "person":
                    person_count += 1
        return person_count
    except Exception as e:
        print(f"[VISION] YOLO person counting error: {e}")
        return 0

def analyze_visual_disaster(image_path: str) -> Dict[str, Any]:
    """
    Classifies image into FLOOD, FIRE, RESCUE (collapse), or UNKNOWN.
    Rules:
    - Never uses filename-based cheats.
    - If GEMINI_API_KEY is configured and Gemini Vision succeeds with conf >= 0.85, marks verified=True.
    - Color/edge/texture heuristic is capped at 0.80 confidence (status=MANUAL_REVIEW, verified=False).
    - Summary explicitly notes when heuristic is used.
    """
    phash_hex = compute_image_phash(image_path)

    # 1. Count persons via YOLO COCO model
    person_count = count_people_yolo(image_path)

    # 2. Check for real vision classifier (Google Gemini Vision)
    active_key = os.getenv("GEMINI_API_KEY") or GEMINI_API_KEY
    if active_key:
        gemini_result = classify_with_gemini_vision(image_path, active_key)
        if gemini_result and gemini_result.get("confidence", 0) >= 0.85:
            conf = gemini_result["confidence"]
            cat = gemini_result["category"]
            sev = gemini_result["severity"]
            tot_persons = max(person_count, gemini_result.get("person_count", 0))
            if tot_persons > 0:
                sev = min(10, sev + 1)
            return {
                "category": cat,
                "confidence": round(float(conf), 2),
                "severity": sev,
                "status": "DISPATCHED",
                "verified": True,
                "phash": phash_hex,
                "summary": gemini_result["summary"],
                "person_count": tot_persons
            }

    # 3. Color, edge, and texture heuristic (weak signal, capped at 0.80)
    img_bgr = cv2.imread(image_path)
    if img_bgr is None:
        return {
            "category": "UNKNOWN",
            "confidence": 0.30,
            "severity": 5,
            "status": "MANUAL_REVIEW",
            "verified": False,
            "phash": phash_hex,
            "summary": "Visual hazard analysis (color/edge heuristic): Unreadable image file.",
            "person_count": person_count
        }

    h, w, _ = img_bgr.shape
    total_pixels = h * w

    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    # (a) Fire / combustion analysis (orange/yellow/red high-saturation high-value spectrum)
    fire_mask1 = cv2.inRange(hsv, np.array([0, 110, 120]), np.array([25, 255, 255]))
    fire_mask2 = cv2.inRange(hsv, np.array([170, 110, 120]), np.array([180, 255, 255]))
    fire_pixels = cv2.countNonZero(fire_mask1 | fire_mask2)
    fire_ratio = fire_pixels / max(1, total_pixels)

    # (b) Flood / water analysis (saturated blue-cyan or muddy river flood water)
    water_mask1 = cv2.inRange(hsv, np.array([85, 80, 50]), np.array([135, 255, 255]))
    water_mask2 = cv2.inRange(hsv, np.array([15, 80, 50]), np.array([30, 255, 200]))
    water_pixels = cv2.countNonZero(water_mask1 | water_mask2)
    water_ratio = water_pixels / max(1, total_pixels)

    # (c) Collapse / rubble / structural hazard analysis
    # High-frequency Laplacian texture variation combined with desaturated concrete/masonry tones
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    edges = cv2.Canny(gray, 80, 180)
    edge_ratio = cv2.countNonZero(edges) / max(1, total_pixels)
    sat_mean = float(hsv[:, :, 1].mean())

    # Weak heuristic scoring, capped strictly at 0.80 so it can NEVER reach verified alone (>= 0.85)
    fire_score = min(0.80, fire_ratio * 3.5) if fire_ratio > 0.04 else 0.10
    water_score = min(0.80, water_ratio * 3.0) if water_ratio > 0.05 else 0.10

    collapse_score = 0.10
    if laplacian_var > 1500 and sat_mean < 90:
        collapse_score = min(0.80, 0.50 + (laplacian_var / 10000.0) * 0.30)
    elif edge_ratio > 0.06 and sat_mean < 90:
        collapse_score = min(0.80, 0.40 + edge_ratio * 3.0)

    scores = [
        ("FIRE", fire_score),
        ("FLOOD", water_score),
        ("RESCUE", collapse_score)
    ]
    scores.sort(key=lambda x: x[1], reverse=True)
    best_cat, best_conf = scores[0]

    # If all signals are low/negligible, classify as UNKNOWN
    if best_conf < 0.35:
        best_cat = "UNKNOWN"
        best_conf = 0.30
        severity = 5
        summary = "Visual hazard analysis (color/edge heuristic): Inconclusive visual signal. Operator review required."
    else:
        # Cap strictly at 0.80
        best_conf = min(0.80, float(best_conf))

        if best_cat == "FIRE":
            severity = 8
            summary = "Visual hazard analysis (color/edge heuristic): Fire and combustion spectrum detected."
        elif best_cat == "FLOOD":
            severity = 7
            summary = "Visual hazard analysis (color/edge heuristic): Water accumulation and flood signature detected."
        elif best_cat == "RESCUE":
            severity = 8
            summary = "Visual hazard analysis (color/edge heuristic): Structural rubble and debris texture detected."
        else:
            severity = 5
            summary = "Visual hazard analysis (color/edge heuristic): Incident requires inspection."

    if person_count > 0:
        severity = min(10, severity + 1)
        summary += f" ({person_count} person(s) detected by YOLO)."

    # Never auto-dispatch heuristic without operator confirmation
    # Confidence <= 0.80 -> MANUAL_REVIEW, verified=False
    status = "MANUAL_REVIEW"
    verified = False

    return {
        "category": best_cat,
        "confidence": round(float(best_conf), 2),
        "severity": severity,
        "status": status,
        "verified": verified,
        "phash": phash_hex,
        "summary": summary,
        "person_count": person_count
    }
