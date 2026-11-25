import uuid
import datetime
import enum
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, Enum, ForeignKey, Index, Boolean
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class ViolationType(str, enum.Enum):
    NO_HELMET = "NO_HELMET"
    TRIPLE_RIDING = "TRIPLE_RIDING"
    SPEEDING = "SPEEDING"
    RED_LIGHT = "RED_LIGHT"
    HAZARD_BLOCK = "HAZARD_BLOCK"

class ViolationStatus(str, enum.Enum):
    PENDING = "PENDING"
    CHALLAN_ISSUED = "CHALLAN_ISSUED"
    DISMISSED = "DISMISSED"

class ChallanStatus(str, enum.Enum):
    ISSUED = "ISSUED"
    PAID = "PAID"
    DISMISSED = "DISMISSED"

class HazardCategory(str, enum.Enum):
    POTHOLE = "POTHOLE"
    GARBAGE_DUMP = "GARBAGE_DUMP"
    BROKEN_BARRIER = "BROKEN_BARRIER"
    WATERLOGGING = "WATERLOGGING"
    SIGNAL_FAILURE = "SIGNAL_FAILURE"
    ROAD_CRACK = "ROAD_CRACK"

class HazardStatus(str, enum.Enum):
    REPORTED = "REPORTED"
    IN_REVIEW = "IN_REVIEW"
    DISPATCHED = "DISPATCHED"
    RESOLVED = "RESOLVED"
    REJECTED = "REJECTED"

class HazardPriority(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class Violation(Base):
    __tablename__ = "violations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    idempotency_key = Column(String(128), unique=True, index=True, nullable=False)
    camera_id = Column(String(64), index=True, nullable=False)
    location_name = Column(String(255), nullable=False)
    zone_id = Column(String(64), index=True, nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    violation_type = Column(String(32), nullable=False)
    confidence = Column(Float, default=0.0)
    plate_number = Column(String(32), index=True, nullable=True)
    raw_frame_url = Column(String(512), nullable=True)
    crop_url = Column(String(512), nullable=True)
    status = Column(String(32), default=ViolationStatus.PENDING.value, index=True)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)

    challan = relationship("Challan", back_populates="violation", uselist=False)

    __table_args__ = (
        Index("idx_violations_plate_created", "plate_number", "created_at"),
        Index("idx_violations_zone_type", "zone_id", "violation_type"),
    )

class Challan(Base):
    __tablename__ = "challans"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    challan_number = Column(String(64), unique=True, index=True, nullable=False)
    idempotency_key = Column(String(128), unique=True, index=True, nullable=False)
    violation_id = Column(String(36), ForeignKey("violations.id"), unique=True, nullable=False)
    plate_number = Column(String(32), index=True, nullable=False)
    violation_type = Column(String(32), nullable=False)
    fine_amount = Column(Float, nullable=False, default=1000.0)
    due_date = Column(DateTime, nullable=False)
    status = Column(String(32), default=ChallanStatus.ISSUED.value, index=True)
    evidence_url = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    paid_at = Column(DateTime, nullable=True)

    violation = relationship("Violation", back_populates="challan")

class CitizenReport(Base):
    __tablename__ = "citizen_reports"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    ticket_id = Column(String(64), unique=True, index=True, nullable=False)
    idempotency_key = Column(String(128), unique=True, index=True, nullable=False)
    category = Column(String(32), nullable=False, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    address = Column(String(255), nullable=False)
    zone_id = Column(String(64), index=True, nullable=False)
    description = Column(Text, nullable=False)
    media_url = Column(String(512), nullable=True)
    status = Column(String(32), default=HazardStatus.REPORTED.value, index=True)
    priority = Column(String(32), default=HazardPriority.MEDIUM.value)
    assigned_department = Column(String(128), nullable=True)
    notes = Column(Text, nullable=True)
    reporter_contact = Column(String(128), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    __table_args__ = (
        Index("idx_reports_zone_status", "zone_id", "status"),
        Index("idx_reports_category_created", "category", "created_at"),
    )

class HotspotZone(Base):
    __tablename__ = "hotspot_zones"

    zone_id = Column(String(64), primary_key=True)
    zone_name = Column(String(128), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    radius_meters = Column(Float, default=500.0)
    violation_count = Column(Integer, default=0)
    hazard_count = Column(Integer, default=0)
    risk_level = Column(String(32), default="LOW")
    last_updated = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    entity_type = Column(String(64), index=True, nullable=False)
    entity_id = Column(String(64), index=True, nullable=False)
    action = Column(String(64), nullable=False)
    actor = Column(String(128), nullable=False)
    details = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
