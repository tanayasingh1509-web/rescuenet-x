#!/usr/bin/env python3
"""
Test Suite: Section 4.5 Schema Contract and Validation
Verifies:
1. EventPayload strictly conforms to Section 4.5 contract (10 canonical fields)
2. Invalid enum values (category, source) raise ValidationError (HTTP 422)
3. Coordinates out of bounds (lat > 90, lng > 180) raise ValidationError
4. Severity out of bounds (1..10) raises ValidationError
5. Casualty count < 0 raises ValidationError
"""

import sys
from pathlib import Path
from pydantic import ValidationError

# Add project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.schemas import EventPayload, Coordinates, PWAReportRequest

def test_canonical_section_4_5_schema_valid():
    valid_data = {
        "id": "EVENT_VALID_01",
        "category": "FLOOD",
        "severity": 8,
        "casualty_count": 3,
        "coordinates": {"lat": 28.6145, "lng": 77.2085},
        "sector": "Sector 18 East",
        "summary": "Severe flash flood reported near main highway",
        "confidence": 0.94,
        "source": "pwa",
        "raw_transcript": "Water level rising fast",
        "verified": True
    }

    event = EventPayload(**valid_data)
    assert event.id == "EVENT_VALID_01"
    assert event.category == "FLOOD"
    assert event.severity == 8
    assert event.casualty_count == 3
    assert event.coordinates.lat == 28.6145
    assert event.coordinates.lng == 77.2085
    assert event.sector == "Sector 18 East"
    assert event.confidence == 0.94
    assert event.source == "pwa"
    assert event.verified is True

def test_invalid_category_raises_validation_error():
    invalid_data = {
        "id": "EV_BAD_CAT",
        "category": "METEOR_STRIKE", # Not in allowed Literal
        "severity": 5,
        "casualty_count": 0,
        "coordinates": {"lat": 28.61, "lng": 77.20},
        "sector": "Sector 1",
        "summary": "Test incident",
        "confidence": 0.8,
        "source": "pwa"
    }

    try:
        EventPayload(**invalid_data)
        assert False, "Failed: Invalid category must raise ValidationError"
    except ValidationError as e:
        assert "category" in str(e)

def test_invalid_source_raises_validation_error():
    invalid_data = {
        "id": "EV_BAD_SRC",
        "category": "FIRE",
        "severity": 5,
        "casualty_count": 0,
        "coordinates": {"lat": 28.61, "lng": 77.20},
        "sector": "Sector 1",
        "summary": "Test incident",
        "confidence": 0.8,
        "source": "unauthorized_social_media" # Not in allowed Literal
    }

    try:
        EventPayload(**invalid_data)
        assert False, "Failed: Invalid source must raise ValidationError"
    except ValidationError as e:
        assert "source" in str(e)

def test_out_of_bounds_coordinates_raises_validation_error():
    # Lat > 90
    try:
        Coordinates(lat=95.0, lng=77.20)
        assert False, "Failed: Latitude > 90 must raise ValidationError"
    except ValidationError as e:
        assert "lat" in str(e)

    # Lng < -180
    try:
        Coordinates(lat=28.61, lng=-195.0)
        assert False, "Failed: Longitude < -180 must raise ValidationError"
    except ValidationError as e:
        assert "lng" in str(e)

def test_out_of_bounds_severity_raises_validation_error():
    # Severity > 10
    try:
        EventPayload(
            id="EV_BAD_SEV",
            category="AMBULANCE",
            severity=15, # Max is 10
            casualty_count=1,
            coordinates={"lat": 28.61, "lng": 77.20},
            sector="Sector 1",
            summary="Test",
            confidence=0.8,
            source="voice"
        )
        assert False, "Failed: Severity > 10 must raise ValidationError"
    except ValidationError as e:
        assert "severity" in str(e)

def test_negative_casualty_count_raises_validation_error():
    try:
        EventPayload(
            id="EV_BAD_CAS",
            category="POLICE",
            severity=5,
            casualty_count=-2, # Min is 0
            coordinates={"lat": 28.61, "lng": 77.20},
            sector="Sector 1",
            summary="Test",
            confidence=0.8,
            source="pwa"
        )
        assert False, "Failed: Casualty count < 0 must raise ValidationError"
    except ValidationError as e:
        assert "casualty_count" in str(e)

def test_pwa_report_request_contract():
    req = PWAReportRequest(
        category="RESCUE",
        lat=28.6145,
        lng=77.2085,
        sector="Sector 18 Block B",
        casualty_count=2,
        severity=9,
        description="Immediate extraction required from 3rd floor"
    )
    assert req.category == "RESCUE"
    assert req.lat == 28.6145
    assert req.casualty_count == 2

    # Negative casualty in PWA request
    try:
        PWAReportRequest(
            category="RESCUE",
            lat=28.6145,
            lng=77.2085,
            sector="Sector 18",
            casualty_count=-1
        )
        assert False, "Failed: Negative casualties in PWA request must fail"
    except ValidationError:
        pass

if __name__ == "__main__":
    print("Running Section 4.5 Schema Contract & Validation Test Suite...")
    test_canonical_section_4_5_schema_valid()
    print("  ✓ Canonical Section 4.5 payload validates all 10 schema fields")
    test_invalid_category_raises_validation_error()
    print("  ✓ Invalid category raises ValidationError (HTTP 422)")
    test_invalid_source_raises_validation_error()
    print("  ✓ Invalid source channel raises ValidationError (HTTP 422)")
    test_out_of_bounds_coordinates_raises_validation_error()
    print("  ✓ Out of bounds coordinates (lat > 90, lng < -180) raise ValidationError")
    test_out_of_bounds_severity_raises_validation_error()
    print("  ✓ Out of bounds severity (> 10) raises ValidationError")
    test_negative_casualty_count_raises_validation_error()
    print("  ✓ Negative casualty count (< 0) raises ValidationError")
    test_pwa_report_request_contract()
    print("  ✓ Citizen PWA report schema contract validated")
    print("✅ All schema contract tests passed!")
