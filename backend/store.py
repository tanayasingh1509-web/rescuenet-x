"""
Persistent Store for RESCUENET-X backed by SQLite.
Thread-safe and async-safe: manages events, units, deduplication clusters, and dispatch audit logs.
Data survives server restarts.
"""

import math
import time
import json
import threading
import asyncio
from typing import List, Optional, Dict, Any

from .schemas import EventPayload, RescueUnit, Coordinates
from .config import DEFAULT_CENTER_LAT, DEFAULT_CENTER_LNG
from .database import get_db_connection, init_db

MAX_EVENTS_CAP = 1000

def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Computes Great Circle distance between two points in meters using Haversine formula."""
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
    """Computes Hamming distance between two hex perceptual hashes."""
    try:
        val1 = int(hash1_hex, 16)
        val2 = int(hash2_hex, 16)
        xor_val = val1 ^ val2
        return bin(xor_val).count('1')
    except Exception:
        return 999

class IncidentStore:
    def __init__(self):
        self._lock = threading.RLock()
        self._async_lock = None  # Lazily instantiated inside running loop
        self._events: Dict[str, EventPayload] = {}
        self._units: Dict[str, RescueUnit] = {}
        init_db()
        self._load_from_db()

    def _get_async_lock(self):
        if self._async_lock is None:
            self._async_lock = asyncio.Lock()
        return self._async_lock

    def _load_from_db(self):
        """Loads events and units from SQLite into fast in-memory cache."""
        with self._lock:
            conn = get_db_connection()
            try:
                cur = conn.cursor()

                # Load units
                cur.execute("SELECT * FROM units")
                unit_rows = cur.fetchall()
                if not unit_rows:
                    self._init_default_units(conn)
                else:
                    self._units.clear()
                    for r in unit_rows:
                        u = RescueUnit(
                            id=r["id"],
                            name=r["name"],
                            unit_type=r["unit_type"],
                            lat=r["lat"],
                            lng=r["lng"],
                            status=r["status"],
                            eta_minutes=r["eta_minutes"],
                            contact=r["contact"]
                        )
                        self._units[u.id] = u

                # Load events
                cur.execute("SELECT * FROM events ORDER BY timestamp DESC LIMIT ?", (MAX_EVENTS_CAP,))
                event_rows = cur.fetchall()
                self._events.clear()
                for r in event_rows:
                    assigned = json.loads(r["assigned_unit"]) if r["assigned_unit"] else None
                    ev = EventPayload(
                        category=r["category"],
                        coordinates=Coordinates(lat=r["lat"], lng=r["lng"]),
                        sector=r["sector"],
                        severity=r["severity"],
                        casualty_count=r["casualty_count"],
                        summary=r["summary"],
                        confidence=r["confidence"],
                        source=r["source"],
                        raw_transcript=r["raw_transcript"],
                        verified=bool(r["verified"]),
                        id=r["id"],
                        timestamp=r["timestamp"],
                        status=r["status"],
                        assigned_unit=assigned,
                        cluster_count=r["cluster_count"],
                        phash=r["phash"],
                        image_url=r["image_url"],
                        raw_severity=r["raw_severity"],
                        urgency=r["urgency"],
                        location_unknown=bool(r["location_unknown"])
                    )
                    self._events[ev.id] = ev
            finally:
                conn.close()

    def _init_default_units(self, conn=None):
        """Initializes default rescue fleet in SQLite and cache."""
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
        close_conn = False
        if conn is None:
            conn = get_db_connection()
            close_conn = True

        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM units")
            self._units.clear()
            for u in defaults:
                cur.execute(
                    "INSERT INTO units (id, name, unit_type, lat, lng, status, eta_minutes, contact) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (u.id, u.name, u.unit_type, u.lat, u.lng, u.status, u.eta_minutes, u.contact)
                )
                self._units[u.id] = u
            conn.commit()
        finally:
            if close_conn:
                conn.close()

    def add_event(self, event: EventPayload) -> EventPayload:
        with self._lock:
            self._events[event.id] = event

            # SQLite insert/replace
            conn = get_db_connection()
            try:
                cur = conn.cursor()
                assigned_str = json.dumps(event.assigned_unit) if event.assigned_unit else None
                cur.execute("""
                INSERT OR REPLACE INTO events (
                    id, category, lat, lng, sector, severity, casualty_count, summary, confidence,
                    source, raw_transcript, verified, status, assigned_unit, cluster_count, phash,
                    image_url, raw_severity, urgency, location_unknown, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event.id, event.category, event.coordinates.lat, event.coordinates.lng,
                    event.sector, event.severity, event.casualty_count, event.summary,
                    event.confidence, event.source, event.raw_transcript, int(event.verified),
                    event.status, assigned_str, event.cluster_count, event.phash,
                    event.image_url, event.raw_severity, event.urgency,
                    int(event.location_unknown), event.timestamp
                ))

                # Cap stored events to MAX_EVENTS_CAP
                if len(self._events) > MAX_EVENTS_CAP:
                    cur.execute("""
                    DELETE FROM events WHERE id NOT IN (
                        SELECT id FROM events ORDER BY timestamp DESC LIMIT ?
                    )
                    """, (MAX_EVENTS_CAP,))
                    # Clean up memory
                    if len(self._events) > MAX_EVENTS_CAP:
                        sorted_keys = sorted(self._events.keys(), key=lambda k: self._events[k].timestamp)
                        for k in sorted_keys[:len(self._events) - MAX_EVENTS_CAP]:
                            del self._events[k]

                conn.commit()
            finally:
                conn.close()

            return event

    def get_event(self, event_id: str) -> Optional[EventPayload]:
        with self._lock:
            return self._events.get(event_id)

    def list_events(self, limit: Optional[int] = None, offset: int = 0) -> List[EventPayload]:
        with self._lock:
            events = sorted(list(self._events.values()), key=lambda e: e.timestamp, reverse=True)
            if limit is not None:
                return events[offset:offset + limit]
            return events[offset:]

    def update_event_status(self, event_id: str, status: str, unit: Optional[Dict[str, Any]] = None) -> Optional[EventPayload]:
        with self._lock:
            ev = self._events.get(event_id)
            if not ev:
                return None
            ev.status = status
            if unit is not None:
                ev.assigned_unit = unit

            # SQLite update
            conn = get_db_connection()
            try:
                cur = conn.cursor()
                assigned_str = json.dumps(ev.assigned_unit) if ev.assigned_unit else None
                cur.execute(
                    "UPDATE events SET status = ?, assigned_unit = ? WHERE id = ?",
                    (status, assigned_str, event_id)
                )
                conn.commit()
            finally:
                conn.close()

            return ev

    def list_units(self) -> List[RescueUnit]:
        with self._lock:
            return list(self._units.values())

    def get_unit(self, unit_id: str) -> Optional[RescueUnit]:
        with self._lock:
            return self._units.get(unit_id)

    def update_unit_status(self, unit_id: str, status: str) -> Optional[RescueUnit]:
        with self._lock:
            unit = self._units.get(unit_id)
            if unit:
                unit.status = status
                conn = get_db_connection()
                try:
                    cur = conn.cursor()
                    cur.execute("UPDATE units SET status = ? WHERE id = ?", (status, unit_id))
                    conn.commit()
                finally:
                    conn.close()
            return unit

    def find_nearest_unit(self, category: str, lat: float, lng: float) -> Optional[RescueUnit]:
        with self._lock:
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

            for unit in self._units.values():
                if unit.status == "AVAILABLE" and unit.unit_type == target_type:
                    dist = haversine_distance_meters(lat, lng, unit.lat, unit.lng)
                    if dist < min_dist:
                        min_dist = dist
                        best_unit = unit

            if not best_unit:
                for unit in self._units.values():
                    if unit.status == "AVAILABLE":
                        dist = haversine_distance_meters(lat, lng, unit.lat, unit.lng)
                        if dist < min_dist:
                            min_dist = dist
                            best_unit = unit

            return best_unit

    def find_duplicate_image(
        self,
        phash_hex: str,
        lat: float,
        lng: float,
        category: str,
        radius_meters: float = 500.0,
        max_hamming: int = 5,
        time_window_seconds: float = 1800.0,
        current_time: Optional[float] = None
    ) -> Optional[EventPayload]:
        if not phash_hex:
            return None

        now = current_time if current_time is not None else time.time()
        with self._lock:
            for event in self._events.values():
                if event.phash and event.coordinates:
                    if category and event.category.upper() != category.upper():
                        continue
                    if abs(now - event.timestamp) > time_window_seconds:
                        continue
                    dist = haversine_distance_meters(lat, lng, event.coordinates.lat, event.coordinates.lng)
                    if dist <= radius_meters:
                        h_dist = hamming_distance(phash_hex, event.phash)
                        if h_dist < max_hamming:
                            return event
            return None

    def find_spatial_duplicate(
        self,
        lat: float,
        lng: float,
        category: Optional[str] = None,
        radius_meters: float = 100.0,
        time_window_seconds: float = 1800.0,
        current_time: Optional[float] = None
    ) -> Optional[EventPayload]:
        now = current_time if current_time is not None else time.time()
        with self._lock:
            for event in self._events.values():
                if event.coordinates:
                    if category is not None and event.category.upper() != category.upper():
                        continue
                    if abs(now - event.timestamp) > time_window_seconds:
                        continue
                    dist = haversine_distance_meters(lat, lng, event.coordinates.lat, event.coordinates.lng)
                    if dist <= radius_meters:
                        return event
            return None

    def reset(self):
        """Clears all events from SQLite and restores units to initial state."""
        with self._lock:
            conn = get_db_connection()
            try:
                cur = conn.cursor()
                cur.execute("DELETE FROM events")
                cur.execute("DELETE FROM dispatch_log")
                conn.commit()
            finally:
                conn.close()

            self._events.clear()
            self._init_default_units()

# Singleton instance
store = IncidentStore()
