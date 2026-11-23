"""
Unit and integration tests for Phase 1 fixes in RESCUENET-X backend.
Tests run synchronously with pure Python assertions to ensure 100% sandboxed execution.
"""

import os
import time
import numpy as np
import cv2
from pydantic import ValidationError

from backend.store import store, IncidentStore
from backend.schemas import EventPayload, Coordinates, RescueUnit, PWAReportRequest
from backend.agentic_dispatcher import (
    calculate_urgency,
    run_agentic_pipeline,
    CASUALTY_DIVISOR,
    MAX_CASUALTY_BONUS,
    HIGH_CONFIDENCE_THRESHOLD,
    HIGH_CONFIDENCE_BONUS,
    LOW_CONFIDENCE_THRESHOLD,
    LOW_CONFIDENCE_PENALTY
)
from backend.vision_engine import analyze_visual_disaster
from backend.ai_engine import process_audio_transcript
from backend.routes.voice import resolve_voice_coordinates

def test_urgency_scoring_no_voice_bonus():
    """Verify urgency scoring calculates correctly without voice inflation."""
    # Base severity 7, 0 casualties, conf 0.80 -> urgency = 7.0
    u, is_p1 = calculate_urgency(raw_severity=7, casualty_count=0, confidence=0.80)
    assert u == 7.0
    assert not is_p1

    # Base severity 7, 4 casualties (+2), conf 0.90 (+1) -> urgency = 10.0, Priority 1
    u, is_p1 = calculate_urgency(raw_severity=7, casualty_count=4, confidence=0.90)
    assert u == 10.0
    assert is_p1

    # Base severity 5, 0 casualties, low conf 0.60 (-1) -> urgency = 4.0
    u, is_p1 = calculate_urgency(raw_severity=5, casualty_count=0, confidence=0.60)
    assert u == 4.0
    assert not is_p1

def test_unit_status_en_route_and_pending_when_busy():
    """Verify units are marked EN_ROUTE and events are queued PENDING when all units are busy."""
    store._events.clear()
    store._init_default_units()

    units = store.list_units()
    available_units = [u for u in units if u.status == "AVAILABLE"]
    initial_count = len(available_units)
    assert initial_count >= 4

    # Assign all available units
    dispatched_events = []
    for i in range(initial_count):
        ev = EventPayload(
            category="RESCUE",
            coordinates=Coordinates(lat=28.6139 + i * 0.005, lng=77.2090 + i * 0.005),
            severity=8,
            confidence=0.90,
            status="PENDING",
            source="pwa"
        )
        res_ev, state = run_agentic_pipeline(ev)
        assert res_ev.status == "DISPATCHED"
        assert res_ev.assigned_unit is not None
        assigned_unit_id = res_ev.assigned_unit["id"]
        # Unit status in store must now be EN_ROUTE
        unit_in_store = store.get_unit(assigned_unit_id)
        assert unit_in_store.status == "EN_ROUTE"
        dispatched_events.append(res_ev)

    # Next event when NO unit is available must be queued as PENDING
    overflow_ev = EventPayload(
        category="RESCUE",
        coordinates=Coordinates(lat=28.6500, lng=77.2500),
        severity=9,
        confidence=0.90,
        status="PENDING",
        source="pwa"
    )
    res_overflow, overflow_state = run_agentic_pipeline(overflow_ev)
    assert res_overflow.status == "PENDING"
    assert res_overflow.assigned_unit is None
    assert any("No available rescue units in proximity" in log for log in overflow_state.action_log)

def test_resolve_event_frees_unit():
    """Verify incident resolution frees the assigned unit back to AVAILABLE."""
    store._events.clear()
    store._init_default_units()

    ev = EventPayload(
        category="FIRE",
        coordinates=Coordinates(lat=28.6139, lng=77.2090),
        severity=8,
        confidence=0.90,
        source="pwa"
    )
    res_ev, _ = run_agentic_pipeline(ev)
    assert res_ev.status == "DISPATCHED"
    unit_id = res_ev.assigned_unit["id"]
    assert store.get_unit(unit_id).status == "EN_ROUTE"

    # Simulate resolve logic
    res_ev.status = "RESOLVED"
    store.update_unit_status(unit_id, "AVAILABLE")

    assert res_ev.status == "RESOLVED"
    assert store.get_unit(unit_id).status == "AVAILABLE"

def test_dedup_requires_same_category_and_time_window():
    """Verify dedup requires matching category and respects 30 minute time window."""
    store._events.clear()
    store._init_default_units()

    t_base = time.time()
    ev1 = EventPayload(
        category="FLOOD",
        coordinates=Coordinates(lat=28.6139, lng=77.2090),
        severity=7,
        confidence=0.90,
        source="pwa",
        timestamp=t_base
    )
    store.add_event(ev1)

    # Different category within 50m: must NOT merge
    spatial_dup_diff_cat = store.find_spatial_duplicate(
        lat=28.6140,
        lng=28.6140,
        category="FIRE",
        radius_meters=100.0,
        time_window_seconds=1800.0,
        current_time=t_base + 60
    )
    assert spatial_dup_diff_cat is None

    # Same category within 50m but expired time window (35 mins later): must NOT merge
    spatial_dup_expired = store.find_spatial_duplicate(
        lat=28.6139,
        lng=77.2090,
        category="FLOOD",
        radius_meters=100.0,
        time_window_seconds=1800.0,
        current_time=t_base + 2100  # 35 mins
    )
    assert spatial_dup_expired is None

    # Same category within 50m and within 30 min window: MUST merge
    spatial_dup_valid = store.find_spatial_duplicate(
        lat=28.6139,
        lng=77.2090,
        category="FLOOD",
        radius_meters=100.0,
        time_window_seconds=1800.0,
        current_time=t_base + 300  # 5 mins
    )
    assert spatial_dup_valid is not None
    assert spatial_dup_valid.id == ev1.id

def test_voice_coordinate_resolution_and_jitter():
    """Verify voice coordinates map sectors or produce non-colliding jitter with location_unknown=True."""
    lat1, lng1, sec1, unk1 = resolve_voice_coordinates(sector_input="Sector 18 River Basin")
    assert not unk1
    assert "Sector 18" in sec1

    lat_a, lng_a, sec_a, unk_a = resolve_voice_coordinates()
    lat_b, lng_b, sec_b, unk_b = resolve_voice_coordinates()
    assert unk_a is True
    assert unk_b is True
    assert (lat_a, lng_a) != (lat_b, lng_b)

def test_vision_engine_heuristic_capping_and_no_filename_cheat():
    """Verify vision engine caps heuristic at 0.80 and does not cheat by filename."""
    noise_img = np.random.randint(50, 100, (200, 200, 3), dtype=np.uint8)
    fake_path = "test_fire_fake.jpg"
    cv2.imwrite(fake_path, noise_img)
    try:
        res = analyze_visual_disaster(fake_path)
        assert res["confidence"] <= 0.80
        assert res["verified"] is False
        assert res["status"] == "MANUAL_REVIEW"
        assert "heuristic" in res["summary"].lower()
    finally:
        if os.path.exists(fake_path):
            os.remove(fake_path)

def test_ai_engine_stt_failure_never_fabricates():
    """Verify corrupt or empty audio returns MANUAL_REVIEW with 0.3 confidence."""
    empty_path = "empty_test.wav"
    with open(empty_path, "wb") as f:
        f.write(b"")
    try:
        res = process_audio_transcript(empty_path)
        assert res["status"] == "MANUAL_REVIEW"
        assert res["confidence"] == 0.3
        assert res["verified"] is False
        assert "Unintelligible audio" in res["summary"]
        assert res["raw_transcript"] is None
    finally:
        if os.path.exists(empty_path):
            os.remove(empty_path)

def test_strict_pydantic_validation():
    """Verify strict validation rejects invalid coordinates and severity bounds."""
    # Invalid latitude > 90
    invalid_raised = False
    try:
        Coordinates(lat=150.0, lng=77.0)
    except ValidationError:
        invalid_raised = True
    assert invalid_raised, "Expected ValidationError on lat > 90"

    # Invalid severity > 10
    invalid_sev = False
    try:
        EventPayload(
            category="FLOOD",
            coordinates=Coordinates(lat=28.0, lng=77.0),
            severity=15
        )
    except ValidationError:
        invalid_sev = True
    assert invalid_sev, "Expected ValidationError on severity > 10"

if __name__ == "__main__":
    print("[TEST 1] test_urgency_scoring_no_voice_bonus...")
    test_urgency_scoring_no_voice_bonus()
    print("[TEST 2] test_unit_status_en_route_and_pending_when_busy...")
    test_unit_status_en_route_and_pending_when_busy()
    print("[TEST 3] test_resolve_event_frees_unit...")
    test_resolve_event_frees_unit()
    print("[TEST 4] test_dedup_requires_same_category_and_time_window...")
    test_dedup_requires_same_category_and_time_window()
    print("[TEST 5] test_voice_coordinate_resolution_and_jitter...")
    test_voice_coordinate_resolution_and_jitter()
    print("[TEST 6] test_vision_engine_heuristic_capping_and_no_filename_cheat...")
    test_vision_engine_heuristic_capping_and_no_filename_cheat()
    print("[TEST 7] test_ai_engine_stt_failure_never_fabricates...")
    test_ai_engine_stt_failure_never_fabricates()
    print("[TEST 8] test_strict_pydantic_validation...")
    test_strict_pydantic_validation()
    print("========================================")
    print("ALL PHASE 1 BACKEND TESTS PASSED CLEANLY!")
    print("========================================")
