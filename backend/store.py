"""
In-memory real-time store for RESCUENET-X.
Manages incident events, rescue units, deduplication clusters, and dispatch logs.
"""

import math
from typing import List, Optional, Dict, Any
from .schemas import EventPayload, RescueUnit, Coordinates
from .config import DEFAULT_CENTER_LAT, DEFAULT_CENTER_LNG

def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Computes Great Circle distance between two points in meters using Haversine formula.
    """
    R = 6371000  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * \
        math.sin(delta_lambda / 2.0) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def hamming_distance(hash1_hex: str, hash2_hex: str) -> int:
    """
    Computes Hamming distance between two hex perceptual hashes.
    """
    try:
        val1 = int(hash1_hex, 16)
        val2 = int(hash2_hex, 16)
        xor_val = val1 ^ val2
        return bin(xor_val).count('1')
    except Exception:
        return 999

class IncidentStore:
    def __init__(self):
        self._events: Dict[str, EventPayload] = {}
        self._units: Dict[str, RescueUnit] = {}
        self._dispatch_log: List[Dict[str, Any]] = []
        self._init_default_units()

    def _init_default_units(self):
        """Initializes default rescue fleet around demo region."""
        defaults = [
            RescueUnit(
                id="NDRF-ALPHA-1",
                name="NDRF Disaster Response Squad Alpha",
                unit_type="RESCUE",
                lat=DEFAULT_CENTER_LAT + 0.008,
                lng=DEFAULT_CENTER_LNG - 0.006,
                status="AVAILABLE",
                eta_minutes=4,
                contact="+91-11-24363260"
            ),
            RescueUnit(
                id="EMS-AMB-102",
                name="Metro Emergency Trauma Ambulance 102",
                unit_type="AMBULANCE",
                lat=DEFAULT_CENTER_LAT - 0.005,
                lng=DEFAULT_CENTER_LNG + 0.007,
                status="AVAILABLE",
                eta_minutes=6,
                contact="+91-102"
            ),
            RescueUnit(
                id="FIRE-TENDER-09",
                name="Hazmat Fire & Heavy Rescue Tender 9",
                unit_type="FIRE",
                lat=DEFAULT_CENTER_LAT + 0.012,
                lng=DEFAULT_CENTER_LNG + 0.009,
                status="AVAILABLE",
                eta_minutes=5,
                contact="+91-101"
            ),
            RescueUnit(
                id="POLICE-PCR-07",
                name="City Rapid Emergency PCR Unit 7",
                unit_type="POLICE",
                lat=DEFAULT_CENTER_LAT - 0.009,
                lng=DEFAULT_CENTER_LNG - 0.008,
                status="AVAILABLE",
                eta_minutes=3,
                contact="+91-112"
            )
        ]
        for u in defaults:
            self._units[u.id] = u

    def add_event(self, event: EventPayload) -> EventPayload:
        self._events[event.id] = event
        return event

    def get_event(self, event_id: str) -> Optional[EventPayload]:
        return self._events.get(event_id)

    def list_events(self) -> List[EventPayload]:
        # Return sorted by timestamp descending
        return sorted(list(self._events.values()), key=lambda e: e.timestamp, reverse=True)

    def update_event_status(self, event_id: str, status: str, unit: Optional[Dict[str, Any]] = None) -> Optional[EventPayload]:
        ev = self._events.get(event_id)
        if not ev:
            return None
        ev.status = status
        if unit:
            ev.assigned_unit = unit
        return ev

    def list_units(self) -> List[RescueUnit]:
        return list(self._units.values())

    def get_unit(self, unit_id: str) -> Optional[RescueUnit]:
        return self._units.get(unit_id)

    def update_unit_status(self, unit_id: str, status: str) -> Optional[RescueUnit]:
        unit = self._units.get(unit_id)
        if unit:
            unit.status = status
        return unit

    def find_nearest_unit(self, category: str, lat: float, lng: float) -> Optional[RescueUnit]:
        """
        Finds the nearest available rescue unit matching category, or closest available overall.
        """
        category_map = {
            "FIRE": "FIRE",
            "FLOOD": "RESCUE",
            "RESCUE": "RESCUE",
            "AMBULANCE": "AMBULANCE",
            "POLICE": "POLICE"
        }
        target_type = category_map.get(category.upper(), "RESCUE")

        best_unit = None
        min_dist = float("inf")

        # First try matching exact unit_type
        for unit in self._units.values():
            if unit.status == "AVAILABLE" and unit.unit_type == target_type:
                dist = haversine_distance_meters(lat, lng, unit.lat, unit.lng)
                if dist < min_dist:
                    min_dist = dist
                    best_unit = unit

        # If no specific type available, grab nearest available unit
        if not best_unit:
            for unit in self._units.values():
                if unit.status == "AVAILABLE":
                    dist = haversine_distance_meters(lat, lng, unit.lat, unit.lng)
                    if dist < min_dist:
                        min_dist = dist
                        best_unit = unit

        return best_unit

    def find_duplicate_image(self, phash_hex: str, lat: float, lng: float, radius_meters: float = 500.0, max_hamming: int = 5) -> Optional[EventPayload]:
        """
        FR-2.3 & Section 4.4:
        Filter duplicate images using perceptual hashing.
        If images submitted within 500m have Hamming distance < 5, return existing cluster event.
        """
        if not phash_hex:
            return None

        for event in self._events.values():
            if event.phash and event.coordinates:
                dist = haversine_distance_meters(lat, lng, event.coordinates.lat, event.coordinates.lng)
                if dist <= radius_meters:
                    h_dist = hamming_distance(phash_hex, event.phash)
                    if h_dist < max_hamming:
                        return event
        return None

    def find_spatial_duplicate(self, lat: float, lng: float, radius_meters: float = 100.0, category: Optional[str] = None) -> Optional[EventPayload]:
        """
        Section 4.4:
        General spatial-merge radius of 100m for mixed-source event clustering.
        """
        for event in self._events.values():
            if event.coordinates:
                dist = haversine_distance_meters(lat, lng, event.coordinates.lat, event.coordinates.lng)
                if dist <= radius_meters:
                    if category is None or category.upper() == event.category.upper():
                        return event
        return None

# Singleton instance
store = IncidentStore()
