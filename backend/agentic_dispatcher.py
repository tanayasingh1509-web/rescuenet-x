"""
Agentic Dispatcher for RESCUENET-X
Implements an agentic state-flow pipeline fulfilling Section 4.4:
1. Deduplication Agent:
   - 500m radius + Hamming distance < 5 for image pHash deduplication
   - 100m radius for general mixed-source spatial deduplication & event clustering
2. Urgency Scoring Agent:
   - Dynamic Urgency Score (1-10) combining severity, casualty count, and confidence
3. Routing & Unit Dispatch Agent:
   - Calculates optimal routing to the nearest available unit via Haversine distance
"""

import math
from typing import Dict, Any, Optional, Tuple
from .schemas import EventPayload, RescueUnit
from .store import store, haversine_distance_meters, hamming_distance

class DispatcherState:
    """State object passed through agentic pipeline nodes."""
    def __init__(self, event: EventPayload):
        self.event: EventPayload = event
        self.is_duplicate: bool = False
        self.merged_into_event_id: Optional[str] = None
        self.assigned_unit: Optional[Dict[str, Any]] = None
        self.action_log: list = []

def deduplication_agent(state: DispatcherState) -> DispatcherState:
    """
    Node 1: Evaluates Spatial & Perceptual Hash Deduplication.
    - 500m radius + Hamming < 5 for image dedup (FR-2.3)
    - 100m radius general spatial merge for mixed sources (Section 4.4)
    """
    event = state.event
    lat = event.coordinates.lat
    lng = event.coordinates.lng

    # 1. Image Perceptual Hash Deduplication (500m radius, Hamming < 5)
    if event.phash and event.source == "image":
        dup_event = store.find_duplicate_image(
            phash_hex=event.phash,
            lat=lat,
            lng=lng,
            radius_meters=500.0,
            max_hamming=5
        )
        if dup_event and dup_event.id != event.id:
            state.is_duplicate = True
            state.merged_into_event_id = dup_event.id
            dup_event.cluster_count += 1
            # Update severity/casualty if the new incoming report reports higher casualties
            dup_event.casualty_count = max(dup_event.casualty_count, event.casualty_count)
            dup_event.severity = max(dup_event.severity, event.severity)
            state.action_log.append(
                f"[DEDUP-AGENT] Image merged into existing cluster #{dup_event.id} (pHash match within 500m)."
            )
            return state

    # 2. Mixed-source General Spatial Deduplication (100m radius)
    spatial_dup = store.find_spatial_duplicate(
        lat=lat,
        lng=lng,
        radius_meters=100.0,
        category=event.category
    )
    if spatial_dup and spatial_dup.id != event.id:
        state.is_duplicate = True
        state.merged_into_event_id = spatial_dup.id
        spatial_dup.cluster_count += 1
        spatial_dup.casualty_count = max(spatial_dup.casualty_count, event.casualty_count)
        spatial_dup.severity = max(spatial_dup.severity, event.severity)
        state.action_log.append(
            f"[DEDUP-AGENT] Mixed-source report merged into cluster #{spatial_dup.id} (spatial proximity < 100m)."
        )
        return state

    state.action_log.append("[DEDUP-AGENT] Verified as novel incident event.")
    return state

def urgency_scorer_agent(state: DispatcherState) -> DispatcherState:
    """
    Node 2: Assigns dynamic Urgency Score (1 to 10) combining severity from NLP and Vision.
    """
    if state.is_duplicate:
        return state

    event = state.event
    base_severity = event.severity  # 1 to 10 from NLP or Vision

    # Casualty weight: +1 urgency per 2 casualties, capped at +3
    casualty_factor = min(3, event.casualty_count // 2)

    # Verification / Confidence weight
    confidence_factor = 0
    if event.confidence >= 0.85:
        confidence_factor = 1
    elif event.confidence < 0.70:
        confidence_factor = -1

    # Source weight: Voice 2G / DTMF in crisis has high human urgency
    source_weight = 1 if event.source == "voice" else 0

    composite_score = base_severity + casualty_factor + confidence_factor + source_weight
    final_urgency = max(1, min(10, composite_score))

    event.severity = final_urgency
    state.action_log.append(
        f"[URGENCY-AGENT] Dynamic Urgency computed: {final_urgency}/10 (Base: {base_severity}, Casualties: {event.casualty_count})."
    )
    return state

def routing_agent(state: DispatcherState) -> DispatcherState:
    """
    Node 3: Calculates optimal routing to nearest available Rescue Unit / Ambulance.
    """
    if state.is_duplicate:
        return state

    event = state.event

    # If flagged for manual review (< 0.70 confidence), hold automatic dispatch
    if event.status == "MANUAL_REVIEW":
        state.action_log.append(
            "[ROUTING-AGENT] Low confidence (<0.70). Holding auto-dispatch for Operator Review."
        )
        return state

    nearest_unit: Optional[RescueUnit] = store.find_nearest_unit(
        category=event.category,
        lat=event.coordinates.lat,
        lng=event.coordinates.lng
    )

    if nearest_unit:
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
            "contact": nearest_unit.contact
        }

        event.assigned_unit = assigned_dict
        event.status = "DISPATCHED"
        state.assigned_unit = assigned_dict

        state.action_log.append(
            f"[ROUTING-AGENT] Auto-routed to {nearest_unit.name} ({dist_km:.2f} km away, ETA {eta_mins} mins)."
        )
    else:
        state.action_log.append("[ROUTING-AGENT] No idle unit available in proximity. Placed in priority queue.")

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
