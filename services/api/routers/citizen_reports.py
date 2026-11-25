import uuid
import datetime
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Header, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import desc
from services.common.models import CitizenReport, HazardStatus, HazardPriority, HotspotZone
from services.common.schemas import (
    CitizenReportCreate,
    CitizenReportResponse,
    CitizenReportUpdate
)
from services.common.storage import storage_service
from services.api.dependencies import get_db, get_redis_client, verify_authority_role

logger = logging.getLogger("suitms.api.citizen_reports")
router = APIRouter(prefix="/citizen-reports", tags=["Citizen Infrastructure Hazard Reporting"])

@router.post("", response_model=CitizenReportResponse, status_code=status.HTTP_201_CREATED, summary="Submit Citizen Hazard Report")
def submit_hazard_report(
    report_in: CitizenReportCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db)
):
    """
    Submits a civic infrastructure hazard report (potholes, garbage, broken guardrails).
    Enforces idempotency: repeated submissions with the same Idempotency-Key return the existing record.
    """
    effective_key = idempotency_key or f"REP:{report_in.category}:{report_in.latitude:.4f}:{report_in.longitude:.4f}:{int(datetime.datetime.utcnow().timestamp() // 300)}"
    
    # Check for existing report with this idempotency key
    existing = db.query(CitizenReport).filter(CitizenReport.idempotency_key == effective_key).first()
    if existing:
        logger.info(f"Duplicate citizen report handled idempotently for key={effective_key}")
        return existing

    ticket_id = f"HAZ-{datetime.datetime.utcnow().year}-{uuid.uuid4().hex[:6].upper()}"
    
    # Priority evaluation
    priority = HazardPriority.MEDIUM.value
    if report_in.category in ["POTHOLE", "BROKEN_BARRIER"]:
        priority = HazardPriority.HIGH.value
    elif report_in.category in ["SIGNAL_FAILURE"]:
        priority = HazardPriority.CRITICAL.value

    report = CitizenReport(
        ticket_id=ticket_id,
        idempotency_key=effective_key,
        category=report_in.category.value,
        latitude=report_in.latitude,
        longitude=report_in.longitude,
        address=report_in.address,
        zone_id=report_in.zone_id or "ZONE-CENTRAL-01",
        description=report_in.description,
        media_url=None,
        status=HazardStatus.REPORTED.value,
        priority=priority,
        reporter_contact=report_in.reporter_contact,
        created_at=datetime.datetime.utcnow(),
    )
    db.add(report)

    # Increment hazard count on zone
    hotspot = db.query(HotspotZone).filter(HotspotZone.zone_id == report.zone_id).first()
    if hotspot:
        hotspot.hazard_count += 1
        
    db.commit()
    db.refresh(report)

    # Broadcast notification to dashboard via Redis
    r_client = get_redis_client()
    if r_client:
        try:
            import json
            r_client.publish("events:broadcast", json.dumps({
                "type": "NEW_HAZARD_REPORT",
                "ticket_id": report.ticket_id,
                "category": report.category,
                "priority": report.priority,
                "address": report.address,
                "created_at": report.created_at.isoformat()
            }))
        except Exception as e:
            logger.warning(f"Failed to publish hazard event: {e}")

    logger.info(f"New civic hazard report created: {report.ticket_id} ({report.category})")
    return report

@router.post("/upload-evidence", summary="Upload Citizen Report Image")
def upload_report_media(file: UploadFile = File(...)):
    """Uploads citizen media to object storage and returns public URL."""
    url = storage_service.store_file(file.file, "suitms-hazards", extension=file.filename.split(".")[-1] if file.filename else "jpg")
    return {"media_url": url}

@router.get("", response_model=List[CitizenReportResponse], summary="Query Hazard Reports")
def list_reports(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status: Optional[str] = None,
    category: Optional[str] = None,
    zone_id: Optional[str] = None,
    priority: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Retrieves paginated hazard reports with filters."""
    query = db.query(CitizenReport)
    if status:
        query = query.filter(CitizenReport.status == status)
    if category:
        query = query.filter(CitizenReport.category == category)
    if zone_id:
        query = query.filter(CitizenReport.zone_id == zone_id)
    if priority:
        query = query.filter(CitizenReport.priority == priority)
        
    return query.order_by(desc(CitizenReport.created_at)).offset(skip).limit(limit).all()

@router.get("/{ticket_id}", response_model=CitizenReportResponse, summary="Lookup Report by Ticket ID")
def get_report_by_ticket(ticket_id: str, db: Session = Depends(get_db)):
    """Citizen tracking endpoint to verify status and notes for a submitted ticket."""
    report = db.query(CitizenReport).filter(CitizenReport.ticket_id == ticket_id.strip().upper()).first()
    if not report:
        raise HTTPException(status_code=404, detail="Hazard report ticket not found.")
    return report

@router.patch("/{ticket_id}", response_model=CitizenReportResponse, summary="Authority Update Report Status")
def update_report(
    ticket_id: str,
    update: CitizenReportUpdate,
    db: Session = Depends(get_db),
    auth: dict = Depends(verify_authority_role)
):
    """Authority endpoint to triage, assign departments, and update ticket lifecycle status."""
    report = db.query(CitizenReport).filter(CitizenReport.ticket_id == ticket_id.strip().upper()).first()
    if not report:
        raise HTTPException(status_code=404, detail="Hazard report ticket not found.")
        
    if update.status:
        report.status = update.status.value
    if update.assigned_department:
        report.assigned_department = update.assigned_department
    if update.priority:
        report.priority = update.priority.value
    if update.notes:
        report.notes = update.notes
        
    report.updated_at = datetime.datetime.utcnow()
    db.commit()
    db.refresh(report)
    return report
