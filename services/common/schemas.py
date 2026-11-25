from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from services.common.models import ViolationType, ViolationStatus, ChallanStatus, HazardCategory, HazardStatus, HazardPriority

# --- Violation & ALPR Schemas ---
class ViolationBase(BaseModel):
    camera_id: str
    location_name: str
    zone_id: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    violation_type: ViolationType
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    plate_number: Optional[str] = None
    metadata_json: Optional[str] = None

class ViolationCreate(ViolationBase):
    idempotency_key: str
    raw_frame_url: Optional[str] = None
    crop_url: Optional[str] = None

class ViolationResponse(ViolationBase):
    id: str
    idempotency_key: str
    raw_frame_url: Optional[str] = None
    crop_url: Optional[str] = None
    status: str
    created_at: datetime
    challan_id: Optional[str] = None

    class Config:
        from_attributes = True

# --- Challan Schemas ---
class ChallanResponse(BaseModel):
    id: str
    challan_number: str
    violation_id: str
    plate_number: str
    violation_type: str
    fine_amount: float
    due_date: datetime
    status: str
    evidence_url: Optional[str] = None
    created_at: datetime
    paid_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class ChallanUpdate(BaseModel):
    status: ChallanStatus

# --- Citizen Report Schemas ---
class CitizenReportCreate(BaseModel):
    category: HazardCategory
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    address: str
    zone_id: Optional[str] = "ZONE-CENTRAL"
    description: str = Field(..., min_length=5, max_length=1000)
    reporter_contact: Optional[str] = None

class CitizenReportUpdate(BaseModel):
    status: Optional[HazardStatus] = None
    assigned_department: Optional[str] = None
    priority: Optional[HazardPriority] = None
    notes: Optional[str] = None

class CitizenReportResponse(BaseModel):
    id: str
    ticket_id: str
    category: str
    latitude: float
    longitude: float
    address: str
    zone_id: str
    description: str
    media_url: Optional[str] = None
    status: str
    priority: str
    assigned_department: Optional[str] = None
    notes: Optional[str] = None
    reporter_contact: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# --- Hotspot & Analytics Schemas ---
class HotspotResponse(BaseModel):
    zone_id: str
    zone_name: str
    latitude: float
    longitude: float
    radius_meters: float
    violation_count: int
    hazard_count: int
    risk_level: str
    last_updated: datetime

    class Config:
        from_attributes = True

class AnalyticsSummary(BaseModel):
    total_violations_today: int
    active_challans_count: int
    total_fines_collected: float
    pending_fines_amount: float
    open_hazards_count: int
    resolved_hazards_count: int
    hotspots: List[HotspotResponse]
    violations_by_type: Dict[str, int]
    hazards_by_category: Dict[str, int]

# --- Edge Ingestion Payload ---
class EdgeDetectionEvent(BaseModel):
    event_id: str
    camera_id: str
    timestamp: str
    zone_id: str
    location_name: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    detected_objects: List[Dict[str, Any]]
    plate_detected: bool = False
    raw_plate_text: Optional[str] = None
    plate_confidence: float = 0.0
    violation_type: Optional[str] = None
    frame_base64: Optional[str] = None
    crop_base64: Optional[str] = None
