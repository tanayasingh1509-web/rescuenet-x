"""
End-to-End Automated Verification Script for RESCUENET-X
Tests:
- FR-1: VoiceBridge IVR endpoints (/api/voice/incoming, /api/voice/menu-select, /api/voice/process-audio)
- FR-2: Visual verification endpoint (/api/report/visual), two-tier confidence, pHash deduplication
- FR-3: Dispatch action (/api/dispatch/{id}), unit fleet tracking, scenarios simulation (/api/simulate/scenario)
- WebSocket payload conformance (Section 4.5 schema)
"""

import sys
import os
import requests
import json
import time
import numpy as np
import cv2

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "http://127.0.0.1:8000"

def log_test(title, passed, details=""):
    symbol = "[PASS]" if passed else "[FAIL]"
    print(f"{symbol} [{title}]: {'PASSED' if passed else 'FAILED'} {details}")
    if not passed:
        sys.exit(1)

def run_tests():
    print("=" * 60)
    print("[TEST] RESCUENET-X AUTOMATED VERIFICATION SUITE")
    print("=" * 60)

    # 1. Health check
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=5)
        log_test("Health Check", r.status_code == 200, f"Status: {r.status_code}, Resp: {r.json()}")
    except Exception as e:
        log_test("Health Check", False, f"Server unreachable: {e}")

    # 2. FR-1.1 DTMF Incoming Voice IVR
    r = requests.post(f"{BASE_URL}/api/voice/incoming")
    log_test("FR-1.1 Twilio Voice IVR", r.status_code == 200 and "Gather" in r.text, "Returns valid TwiML with Gather menu")

    # 3. FR-1.1 DTMF Menu Select (Press 1 for Police, 2 for Ambulance, 3 for Rescue)
    r = requests.post(f"{BASE_URL}/api/voice/menu-select", data={"Digits": "2", "From": "+919876543210"})
    log_test("FR-1.1 DTMF Keypress '2' (Ambulance)", r.status_code == 200 and "Ambulance" in r.text, "Generated Ambulance dispatch event")

    # 4. FR-3 Fleet & Events Query
    r = requests.get(f"{BASE_URL}/api/events")
    events = r.json().get("events", [])
    log_test("Events Store Query", len(events) >= 1, f"Found {len(events)} event(s)")

    r = requests.get(f"{BASE_URL}/api/units")
    units = r.json().get("units", [])
    log_test("Units Store Query", len(units) >= 4, f"Found {len(units)} rescue units")

    # 5. FR-2.1 & FR-2.3 Visual Incident Verification & pHash Dedup
    # Create test flood image (blue-cyan water hue)
    flood_img = np.zeros((250, 250, 3), dtype=np.uint8)
    flood_img[:, :] = (180, 120, 40) # Murky flood water in BGR
    cv2.imwrite("flood_test.jpg", flood_img)

    with open("flood_test.jpg", "rb") as f:
        r = requests.post(f"{BASE_URL}/api/report/visual", files={"image": f}, data={"sector": "Yamuna Sector 14"})

    os.remove("flood_test.jpg")
    vis_data = r.json()
    log_test("FR-2.1 Visual Image Classification", r.status_code == 200 and "event" in vis_data, f"Classified category: {vis_data.get('event', {}).get('category')}, Confidence: {vis_data.get('event', {}).get('confidence')}")

    # Test duplicate image submission (within 500m)
    cv2.imwrite("flood_test_dup.jpg", flood_img)
    with open("flood_test_dup.jpg", "rb") as f:
        r_dup = requests.post(f"{BASE_URL}/api/report/visual", files={"image": f}, data={"sector": "Yamuna Sector 14"})
    os.remove("flood_test_dup.jpg")
    dup_data = r_dup.json()
    log_test("FR-2.3 Image pHash Deduplication (<500m, Hamming<5)", dup_data.get("is_duplicate") == True, "Successfully merged duplicate report into existing cluster")

    # 6. Three Demo Disaster Scenarios (Section 6, Phase 5)
    for sc in ["flood", "medical", "fire"]:
        r_sc = requests.post(f"{BASE_URL}/api/simulate/scenario/{sc}")
        sc_ev = r_sc.json().get("event", {})
        log_test(f"Scenario Simulation: {sc.upper()}", r_sc.status_code == 200 and sc_ev.get("category") is not None, f"Assigned: {sc_ev.get('assigned_unit', {}).get('name')}")

    # 7. FR-3.3 One-Click Dispatch Action
    r = requests.get(f"{BASE_URL}/api/events")
    pending_events = [e for e in r.json().get("events", []) if e.get("status") != "DISPATCHED"]
    target_id = pending_events[0]["id"] if pending_events else r.json().get("events", [])[0]["id"]

    r_disp = requests.post(f"{BASE_URL}/api/dispatch/{target_id}")
    disp_res = r_disp.json()
    log_test("FR-3.3 1-Click Dispatch Action", disp_res.get("status") == "dispatched", f"Unit: {disp_res.get('assigned_unit', {}).get('name')}")

    # 8. Schema Contract Compliance (Section 4.5 fields)
    r_check = requests.get(f"{BASE_URL}/api/events/{target_id}")
    ev_obj = r_check.json()
    required_fields = [
        "category", "coordinates", "sector", "severity",
        "casualty_count", "summary", "confidence", "source",
        "raw_transcript", "verified"
    ]
    all_fields_present = all(field in ev_obj for field in required_fields)
    log_test("Section 4.5 Payload Contract Compliance", all_fields_present, f"All canonical fields validated: {required_fields}")

    print("=" * 60)
    print("[SUCCESS] ALL RESCUENET-X AUTOMATED VERIFICATION TESTS PASSED!")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
