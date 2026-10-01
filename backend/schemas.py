"""
Pydantic schemas for RESCUENET-X.
Preserves the exact Section 4.5 contract:
{
  "category": "FLOOD | FIRE | POLICE | AMBULANCE | RESCUE | UNKNOWN",
  "coordinates": { "lat": 0.0, "lng": 0.0 },
  "sector": "string",
  "severity": 1,
  "casualty_count": 0,
  "summary": "string",
  "confidence": 0.0,
  "source": "voice | image | pwa",
  "raw_transcript": "string | null",
  "verified": true
}
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
import time
import uuid

class Coordinates(BaseModel):
    lat: float = 0.0
    lng: float = 0.0

class EventPayload(BaseModel):
    # Canonical contract fields (MUST match Section 4.5 verbatim)
    category: str = Field(
        ...,
        description="FLOOD | FIRE | POLICE | AMBULANCE | RESCUE | UNKNOWN"
    )
    coordinates: Coordinates = Field(default_factory=Coordinates)
    sector: str = Field(default="Sector-Unknown")
    severity: int = Field(default=1, ge=1, le=10)
    casualty_count: int = Field(default=0, ge=0)
    summary: str = Field(default="")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    source: str = Field(default="voice", description="voice | image | pwa")
    raw_transcript: Optional[str] = None
    verified: bool = Field(default=False)

    # Operational/dashboard metadata (compatible extensions)
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: float = Field(default_factory=lambda: time.time())
    status: str = Field(default="PENDING", description="PENDING | DISPATCHED | MANUAL_REVIEW")
    assigned_unit: Optional[Dict[str, Any]] = None
    cluster_count: int = Field(default=1)
    phash: Optional[str] = None
    image_url: Optional[str] = None

class RescueUnit(BaseModel):
    id: str
    name: str
    unit_type: str  # RESCUE | AMBULANCE | POLICE | FIRE
    lat: float
    lng: float
    status: str = "AVAILABLE"  # AVAILABLE | DISPATCHED | EN_ROUTE | BUSY
    eta_minutes: int = 5
    contact: str = "+91-9876543210"

class DispatchRequest(BaseModel):
    event_id: str
    unit_id: Optional[str] = None
    operator_notes: Optional[str] = None

class PWAReportRequest(BaseModel):
    category: str
    lat: float
    lng: float
    sector: Optional[str] = None
    severity: int = 5
    casualty_count: int = 0
    description: str
