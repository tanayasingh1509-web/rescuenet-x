#!/usr/bin/env python3
"""
Test Suite: Perceptual Hash and Spatial Deduplication
Verifies:
1. Same category + pHash Hamming < 5 merges
2. Different category + same pHash does NOT merge
3. Same category + distance <= 500m + time <= 30m merges
4. Distance > 500m does NOT merge
5. Time > 30m does NOT merge
"""

import sys
import time
from pathlib import Path

# Add project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.store import IncidentStore
from backend.schemas import EventPayload

def test_phash_dedup_same_category():
    store = IncidentStore()
    store.reset()

    ev1 = EventPayload(
        id="EV_01",
        category="FLOOD",
        sector="Sector 18",
        severity=8,
        casualty_count=2,
        coordinates={"lat": 28.6145, "lng": 77.2085},
        summary="Flood report 1",
        confidence=0.85,
        source="image",
        phash="0000000000000000"
    )
    store.add_event(ev1)

    # Identical phash, same location & category -> Must merge
    match = store.find_duplicate_image("0000000000000000", 28.6145, 77.2085, "FLOOD")
    assert match is not None, "Failed: Same category with matching pHash should merge"
    assert match.id == "EV_01"

    # Hamming distance 1 (< 5), same category -> Must merge
    match_close = store.find_duplicate_image("0000000000000001", 28.6145, 77.2085, "FLOOD")
    assert match_close is not None, "Failed: Same category with Hamming distance < 5 should merge"

def test_phash_dedup_different_category_does_not_merge():
    store = IncidentStore()
    store.reset()

    ev1 = EventPayload(
        id="EV_FIRE_01",
        category="FIRE",
        sector="Sector 18",
        severity=7,
        casualty_count=0,
        coordinates={"lat": 28.6145, "lng": 77.2085},
        summary="Fire incident",
        confidence=0.85,
        source="image",
        phash="1111111111111111"
    )
    store.add_event(ev1)

    # Identical phash & location, but category is FLOOD -> Must NOT merge
    match = store.find_duplicate_image("1111111111111111", 28.6145, 77.2085, "FLOOD")
    assert match is None, "Failed: Different category with identical pHash must NOT merge"

def test_spatial_dedup_within_500m_and_30min():
    store = IncidentStore()
    store.reset()

    now = time.time()
    ev1 = EventPayload(
        id="EV_SPATIAL_01",
        category="RESCUE",
        sector="Sector 18 Block A",
        severity=9,
        casualty_count=3,
        coordinates={"lat": 28.6145, "lng": 77.2085},
        summary="Rescue trapped citizens",
        confidence=0.90,
        source="pwa",
        timestamp=now - 300 # 5 minutes ago
    )
    store.add_event(ev1)

    # 100 meters away, same category, within 30 minutes -> Must merge
    # (~0.0005 deg lat ~ 55m)
    match = store.find_spatial_duplicate(28.6150, 77.2085, "RESCUE", radius_meters=500.0, current_time=now)
    assert match is not None, "Failed: Incident within 500m and 30 minutes must merge"
    assert match.id == "EV_SPATIAL_01"

def test_spatial_dedup_distance_greater_than_500m_does_not_merge():
    store = IncidentStore()
    store.reset()

    now = time.time()
    ev1 = EventPayload(
        id="EV_SPATIAL_02",
        category="RESCUE",
        sector="Sector 18 Block A",
        severity=9,
        casualty_count=3,
        coordinates={"lat": 28.6145, "lng": 77.2085},
        summary="Rescue trapped citizens",
        confidence=0.90,
        source="pwa",
        timestamp=now
    )
    store.add_event(ev1)

    # 1.5 km away (~0.015 deg lat ~ 1.66km) -> Must NOT merge
    match = store.find_spatial_duplicate(28.6300, 77.2085, "RESCUE", radius_meters=500.0, current_time=now)
    assert match is None, "Failed: Incident > 500m away must NOT merge"

def test_spatial_dedup_time_greater_than_30min_does_not_merge():
    store = IncidentStore()
    store.reset()

    now = time.time()
    ev1 = EventPayload(
        id="EV_SPATIAL_03",
        category="RESCUE",
        sector="Sector 18 Block A",
        severity=9,
        casualty_count=3,
        coordinates={"lat": 28.6145, "lng": 77.2085},
        summary="Rescue trapped citizens",
        confidence=0.90,
        source="pwa",
        timestamp=now - 2400 # 40 minutes ago (> 30 min window)
    )
    store.add_event(ev1)

    # Same location, but 40 minutes later -> Must NOT merge
    match = store.find_spatial_duplicate(28.6145, 77.2085, "RESCUE", radius_meters=500.0, current_time=now)
    assert match is None, "Failed: Incident > 30 minutes later must NOT merge"

if __name__ == "__main__":
    print("Running Deduplication Test Suite...")
    test_phash_dedup_same_category()
    print("  ✓ pHash same category merges")
    test_phash_dedup_different_category_does_not_merge()
    print("  ✓ pHash different category does NOT merge")
    test_spatial_dedup_within_500m_and_30min()
    print("  ✓ Spatial dedup <= 500m and <= 30min merges")
    test_spatial_dedup_distance_greater_than_500m_does_not_merge()
    print("  ✓ Spatial dedup > 500m does NOT merge")
    test_spatial_dedup_time_greater_than_30min_does_not_merge()
    print("  ✓ Spatial dedup > 30min does NOT merge")
    print("✅ All deduplication tests passed!")
