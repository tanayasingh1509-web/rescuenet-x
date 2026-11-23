"""
Agentic Dispatcher for RESCUENET-X
Implements an agentic state-flow pipeline fulfilling Section 4.4:
1. Deduplication Agent:
   - 500m radius + Hamming distance < 5 + same category + 30m window for image pHash deduplication
   - 100m radius + same category + 30m window for general mixed-source spatial deduplication & event clustering
2. Urgency Scoring Agent:
   - Dynamic Urgency Score (1-10) combining raw severity, casualty count, and confidence without voice inflation
3. Routing & Unit Dispatch Agent:
   - Calculates optimal routing to the nearest available unit via Haversine distance
   - Updates assigned unit status to EN_ROUTE immediately so units are not double-booked
"""

import math
from typing import Dict, Any, Optional, Tuple
from .schemas import EventPayload, RescueUnit
from .store import store, haversine_distance_meters, hamming_distance

# Configurable constants for Urgency Scoring
CASUALTY_DIVISOR: int = 2
MAX_CASUALTY_BONUS: float = 3.0
HIGH_CONFIDENCE_THRESHOLD: float = 0.85
HIGH_CONFIDENCE_BONUS: float = 1.0
LOW_CONFIDENCE_THRESHOLD: float = 0.70
LOW_CONFIDENCE_PENALTY: float = -1.0
PRIORITY_1_THRESHOLD: float = 8.5
DEFAULT_DEDUP_WINDOW_SECONDS: float = 1800.0  # 30 minutes

class DispatcherState:
    """State object passed through agentic pipeline nodes."""
    def __init__(self, event: EventPayload):
        self.event: EventPayload = event
        self.is_duplicate: bool = False
        self.merged_into_event_id: Optional[str] = None
        self.assigned_unit: Optional[Dict[str, Any]] = None
        self.action_log: list = []

def deduplication_agent(state: DispatcherState, time_window_seconds: float = DEFAULT_DEDUP_WINDOW_SECONDS) -> DispatcherState:
    """
    Node 1: Evaluates Spatial & Perceptual Hash Deduplication.
    - 500m radius + Hamming < 5 + same category + 30m window for image dedup (FR-2.3)
    - 100m radius + same category + 30m window general spatial merge for mixed sources (Section 4.4)
    """
    event = state.event
    lat = event.coordinates.lat
    lng = event.coordinates.lng

    # 1. Image Perceptual Hash Deduplication (500m radius, Hamming < 5, same category, 30 min window)
    if event.phash and event.source == "image":
        dup_event = store.find_duplicate_image(
            phash_hex=event.phash,
            lat=lat,
            lng=lng,
            category=event.category,
            radius_meters=500.0,
            max_hamming=5,
            time_window_seconds=time_window_seconds,
            current_time=event.timestamp
        )
        if dup_event and dup_event.id != event.id:
            state.is_duplicate = True
            state.merged_into_event_id = dup_event.id
            dup_event.cluster_count += 1
            # Merge casualties and severity
            dup_event.casualty_count = max(dup_event.casualty_count, event.casualty_count)
            if event.raw_severity:
                dup_event.raw_severity = max(dup_event.raw_severity or dup_event.severity, event.raw_severity)
            dup_event.severity = max(dup_event.severity, event.severity)
            if event.urgency:
                dup_event.urgency = max(dup_event.urgency or float(dup_event.severity), event.urgency)
            state.action_log.append(
                f"[DEDUP-AGENT] Image merged into existing cluster #{dup_event.id} (pHash match within 500m, same category, 30m window)."
            )
            return state

    # 2. Mixed-source General Spatial Deduplication (100m radius, same category, 30 min window)
    spatial_dup = store.find_spatial_duplicate(
        lat=lat,
        lng=lng,
        category=event.category,
        radius_meters=100.0,
        time_window_seconds=time_window_seconds,
        current_time=event.timestamp
    )
    if spatial_dup and spatial_dup.id != event.id:
        state.is_duplicate = True
        state.merged_into_event_id = spatial_dup.id
        spatial_dup.cluster_count += 1
        spatial_dup.casualty_count = max(spatial_dup.casualty_count, event.casualty_count)
        if event.raw_severity:
            spatial_dup.raw_severity = max(spatial_dup.raw_severity or spatial_dup.severity, event.raw_severity)
        spatial_dup.severity = max(spatial_dup.severity, event.severity)
        if event.urgency:
            spatial_dup.urgency = max(spatial_dup.urgency or float(spatial_dup.severity), event.urgency)
        state.action_log.append(
            f"[DEDUP-AGENT] Mixed-source report merged into cluster #{spatial_dup.id} (spatial proximity < 100m, same category, 30m window)."
        )
        return state

    state.action_log.append("[DEDUP-AGENT] Verified as novel incident event.")
    return state

def calculate_urgency(
    raw_severity: int,
    casualty_count: int,
    confidence: float
) -> Tuple[float, bool]:
    """
    Computes urgency score without artificial voice inflation.
    Returns (urgency, is_priority_1).
    """
    # Casualty bonus: +1 urgency per 2 casualties up to MAX_CASUALTY_BONUS
    casualty_factor = min(MAX_CASUALTY_BONUS, float(casualty_count // CASUALTY_DIVISOR))

    # Verification / Confidence weight
    confidence_factor = 0.0
    if confidence >= HIGH_CONFIDENCE_THRESHOLD:
        confidence_factor = HIGH_CONFIDENCE_BONUS
    elif confidence < LOW_CONFIDENCE_THRESHOLD:
        confidence_factor = LOW_CONFIDENCE_PENALTY

    composite = float(raw_severity) + casualty_factor + confidence_factor
    clamped = max(1.0, min(10.0, round(composite, 1)))
    is_p1 = clamped >= PRIORITY_1_THRESHOLD
    return clamped, is_p1

def urgency_scorer_agent(state: DispatcherState) -> DispatcherState:
    """
    Node 2: Assigns dynamic Urgency Score (1 to 10) combining severity from NLP and Vision.
    Keeps model's raw severity in raw_severity and computes urgency separately.
    Removes +1 voice bonus.
    """
    if state.is_duplicate:
        return state

    event = state.event
    base_severity = event.severity  # 1 to 10 from NLP, Vision, or PWA
    event.raw_severity = base_severity

    urgency, is_p1 = calculate_urgency(base_severity, event.casualty_count, event.confidence)
    event.urgency = urgency
    # For backward-compatible severity views, keep integer severity bounded
    event.severity = int(round(urgency))

    p1_flag = " [PRIORITY 1]" if is_p1 else ""
    state.action_log.append(
        f"[URGENCY-AGENT] Dynamic Urgency computed: {urgency}/10{p1_flag} (Raw Severity: {base_severity}, Casualties: {event.casualty_count}, Conf: {event.confidence:.2f})."
    )
    return state

def routing_agent(state: DispatcherState) -> DispatcherState:
    """
    Node 3: Calculates optimal routing to nearest available Rescue Unit / Ambulance.
    Updates unit status to EN_ROUTE immediately.
    If no unit available, sets event status to PENDING and logs clearly.
    """
    if state.is_duplicate:
        return state

    event = state.event

    # If flagged for manual review (< 0.70 confidence or unverified heuristic), hold automatic dispatch
    if event.status == "MANUAL_REVIEW":
        state.action_log.append(
            "[ROUTING-AGENT] Low confidence (<0.70) or unverified heuristic. Holding auto-dispatch for Operator Review."
        )
        return state

    nearest_unit: Optional[RescueUnit] = store.find_nearest_unit(
        category=event.category,
        lat=event.coordinates.lat,
        lng=event.coordinates.lng
    )

    if nearest_unit:
        # Mark assigned unit busy/en-route immediately
        store.update_unit_status(nearest_unit.id, "EN_ROUTE")

        dist_m = haversine_distance_meters(
            event.coordinates.lat,
            event.coordinates.lng,
            nearest_unit.lat,
            nearest_unit.lng
        )
        dist_km = dist_m / 1000.0

        # Estimated travel time assuming 40 km/h emergency response speed
        eta_mins = max(2, int((dist_km / 40.0) * 60))

        assigned_dict = {
            "id": nearest_unit.id,
            "name": nearest_unit.name,
            "unit_type": nearest_unit.unit_type,
            "distance_km": round(dist_km, 2),
            "eta_minutes": eta_mins,
            "contact": nearest_unit.contact,
            "status": "EN_ROUTE"
        }

        event.assigned_unit = assigned_dict
        event.status = "DISPATCHED"
        state.assigned_unit = assigned_dict

        state.action_log.append(
            f"[ROUTING-AGENT] Auto-routed to {nearest_unit.name} ({dist_km:.2f} km away, ETA {eta_mins} mins). Unit status -> EN_ROUTE."
        )
    else:
        event.status = "PENDING"
        event.assigned_unit = None
        log_msg = "[ROUTING-AGENT] No available rescue units in proximity. Queued as PENDING."
        state.action_log.append(log_msg)
        print(log_msg)

    return state

def run_agentic_pipeline(event: EventPayload) -> Tuple[EventPayload, DispatcherState]:
    """
    Executes the sequential agentic dispatch graph.
    """
    state = DispatcherState(event)

    # 1. Deduplication
    state = deduplication_agent(state)

    # If duplicate, update store and return cluster parent
    if state.is_duplicate and state.merged_into_event_id:
        parent = store.get_event(state.merged_into_event_id)
        if parent:
            return parent, state

    # 2. Urgency Scoring
    state = urgency_scorer_agent(state)

    # 3. Routing
    state = routing_agent(state)

    # Save to incident store
    store.add_event(state.event)

    for log in state.action_log:
        print(log)

    return state.event, state
