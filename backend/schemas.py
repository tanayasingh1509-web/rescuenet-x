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

from typing import Optional, Dict, Any, List, Literal
from pydantic import BaseModel, Field, field_validator
import time
import uuid

CategoryType = Literal["FLOOD", "FIRE", "POLICE", "AMBULANCE", "RESCUE", "UNKNOWN"]
SourceType = Literal["voice", "image", "pwa"]
StatusType = Literal["PENDING", "DISPATCHED", "MANUAL_REVIEW", "RESOLVED"]
UnitStatusType = Literal["AVAILABLE", "EN_ROUTE", "DISPATCHED", "BUSY"]
UnitKindType = Literal["RESCUE", "AMBULANCE", "POLICE", "FIRE"]

class Coordinates(BaseModel):
    lat: float = Field(default=0.0, ge=-90.0, le=90.0)
    lng: float = Field(default=0.0, ge=-180.0, le=180.0)

class EventPayload(BaseModel):
    # Canonical contract fields (MUST match Section 4.5 verbatim)
    category: CategoryType = Field(
        ...,
        description="FLOOD | FIRE | POLICE | AMBULANCE | RESCUE | UNKNOWN"
    )
    coordinates: Coordinates = Field(default_factory=Coordinates)
    sector: str = Field(default="Sector-Unknown", max_length=200)
    severity: int = Field(default=1, ge=1, le=10)
    casualty_count: int = Field(default=0, ge=0, le=500)
    summary: str = Field(default="", max_length=2000)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    source: SourceType = Field(default="voice", description="voice | image | pwa")
    raw_transcript: Optional[str] = Field(default=None, max_length=5000)
    verified: bool = Field(default=False)

    # Operational/dashboard metadata (compatible extensions)
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: float = Field(default_factory=lambda: time.time())
    status: StatusType = Field(default="PENDING", description="PENDING | DISPATCHED | MANUAL_REVIEW | RESOLVED")
    assigned_unit: Optional[Dict[str, Any]] = None
    cluster_count: int = Field(default=1, ge=1)
    phash: Optional[str] = None
    image_url: Optional[str] = None
    raw_severity: Optional[int] = Field(default=None, ge=1, le=10)
    urgency: Optional[float] = Field(default=None, ge=1.0, le=10.0)
    location_unknown: bool = Field(default=False)

    @field_validator("category", mode="before")
    @classmethod
    def validate_category(cls, v: Any) -> str:
        if isinstance(v, str):
            v_upper = v.strip().upper()
            valid = {"FLOOD", "FIRE", "POLICE", "AMBULANCE", "RESCUE", "UNKNOWN"}
            if v_upper in valid:
                return v_upper
        return "UNKNOWN"

    @field_validator("source", mode="before")
    @classmethod
    def validate_source(cls, v: Any) -> str:
        if isinstance(v, str):
            v_lower = v.strip().lower()
            valid = {"voice", "image", "pwa"}
            if v_lower in valid:
                return v_lower
        return "voice"

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v: Any) -> str:
        if isinstance(v, str):
            v_upper = v.strip().upper()
            valid = {"PENDING", "DISPATCHED", "MANUAL_REVIEW", "RESOLVED"}
            if v_upper in valid:
                return v_upper
        return "PENDING"

class RescueUnit(BaseModel):
    id: str
    name: str
    unit_type: UnitKindType  # RESCUE | AMBULANCE | POLICE | FIRE
    lat: float = Field(ge=-90.0, le=90.0)
    lng: float = Field(ge=-180.0, le=180.0)
    status: UnitStatusType = "AVAILABLE"  # AVAILABLE | DISPATCHED | EN_ROUTE | BUSY
    eta_minutes: int = Field(default=5, ge=0, le=120)
    contact: str = "+91-9876543210"

class DispatchRequest(BaseModel):
    event_id: str
    unit_id: Optional[str] = None
    operator_notes: Optional[str] = Field(default=None, max_length=1000)

class PWAReportRequest(BaseModel):
    category: CategoryType = "UNKNOWN"
    lat: float = Field(ge=-90.0, le=90.0)
    lng: float = Field(ge=-180.0, le=180.0)
    sector: Optional[str] = Field(default=None, max_length=200)
    severity: int = Field(default=5, ge=1, le=10)
    casualty_count: int = Field(default=0, ge=0, le=500)
    description: str = Field(..., min_length=1, max_length=2000)

    @field_validator("category", mode="before")
    @classmethod
    def normalize_category(cls, v: Any) -> str:
        if isinstance(v, str):
            v_upper = v.strip().upper()
            valid = {"FLOOD", "FIRE", "POLICE", "AMBULANCE", "RESCUE", "UNKNOWN"}
            if v_upper in valid:
                return v_upper
        return "UNKNOWN"
