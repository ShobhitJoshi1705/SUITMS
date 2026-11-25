import json
import logging
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Header, status, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import desc
from services.common.models import Violation, Challan, ChallanStatus, ViolationStatus
from services.common.schemas import (
    ViolationResponse,
    ChallanResponse,
    ChallanUpdate,
    EdgeDetectionEvent
)
from services.common.config import settings
from services.api.dependencies import get_db, get_redis_client, verify_authority_role

logger = logging.getLogger("suitms.api.violations")
router = APIRouter(prefix="/violations", tags=["Traffic Violations & ALPR"])

@router.post("/ingest", status_code=status.HTTP_202_ACCEPTED, summary="Edge Node Stream Ingestion")
def ingest_edge_event(
    event: EdgeDetectionEvent,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Ingests detection payloads from edge cameras.
    Publishes to Redis Stream for decoupled asynchronous inference worker processing.
    If Redis is unavailable, runs synchronous local processing fallback to ensure zero data loss.
    """
    r_client = get_redis_client()
    event_dict = event.model_dump()

    if r_client:
        try:
            # Publish to Redis Stream
            r_client.xadd(
                settings.REDIS_STREAM_VIOLATIONS,
                {"payload": json.dumps(event_dict)},
                maxlen=10000
            )
            return {"status": "queued", "event_id": event.event_id, "stream": settings.REDIS_STREAM_VIOLATIONS}
        except Exception as e:
            logger.warning(f"Failed to queue to Redis Stream ({e}), executing local fallback.")

    # Synchronous processing fallback
    import sys, os
    worker_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "inference-worker"))
    if worker_dir not in sys.path:
        sys.path.insert(0, worker_dir)
    from worker import InferenceWorker
    
    worker = InferenceWorker()
    result = worker.process_event_payload(db, event_dict)
    return {"status": "processed_sync_fallback", "result": result}

@router.get("", response_model=List[ViolationResponse], summary="Query Traffic Violations")
def list_violations(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    plate_number: Optional[str] = None,
    zone_id: Optional[str] = None,
    violation_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Retrieves paginated violation logs with filters on plate number, zone, and type."""
    query = db.query(Violation)
    if plate_number:
        query = query.filter(Violation.plate_number.ilike(f"%{plate_number.strip()}%"))
    if zone_id:
        query = query.filter(Violation.zone_id == zone_id)
    if violation_type:
        query = query.filter(Violation.violation_type == violation_type)
        
    violations = query.order_by(desc(Violation.created_at)).offset(skip).limit(limit).all()
    
    # Attach challan_id if exists
    results = []
    for v in violations:
        resp = ViolationResponse.model_validate(v)
        if v.challan:
            resp.challan_id = v.challan.id
        results.append(resp)
    return results

@router.get("/challans", response_model=List[ChallanResponse], summary="List Challans")
def list_challans(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    plate_number: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Retrieves paginated Challans. Supports search by vehicle registration number."""
    query = db.query(Challan)
    if plate_number:
        query = query.filter(Challan.plate_number.ilike(f"%{plate_number.strip()}%"))
    if status:
        query = query.filter(Challan.status == status)
        
    return query.order_by(desc(Challan.created_at)).offset(skip).limit(limit).all()

@router.get("/challans/{identifier}", response_model=ChallanResponse, summary="Retrieve Challan by ID or Number")
def get_challan(identifier: str, db: Session = Depends(get_db)):
    """
    Retrieves a Challan by either Challan Number (e.g. CH-2026-XXXXX) or Vehicle Plate.
    """
    challan = db.query(Challan).filter(
        (Challan.challan_number == identifier) | 
        (Challan.plate_number == identifier.upper().strip())
    ).first()
    
    if not challan:
        raise HTTPException(status_code=404, detail="Challan not found for provided number or vehicle plate.")
    return challan

@router.patch("/challans/{challan_number}", response_model=ChallanResponse, summary="Update Challan Status")
def update_challan(
    challan_number: str,
    update: ChallanUpdate,
    db: Session = Depends(get_db),
    auth: dict = Depends(verify_authority_role)
):
    """Updates Challan status (e.g., mark as PAID or DISMISSED). Requires authority role."""
    challan = db.query(Challan).filter(Challan.challan_number == challan_number).first()
    if not challan:
        raise HTTPException(status_code=404, detail="Challan not found.")
        
    challan.status = update.status.value
    if update.status == ChallanStatus.PAID:
        challan.paid_at = datetime.utcnow()
        
    db.commit()
    db.refresh(challan)
    return challan
