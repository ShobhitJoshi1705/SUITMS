import json
import logging
import io
import os
import sys
import uuid
from functools import lru_cache
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, Header, status, BackgroundTasks, File, UploadFile
from PIL import Image, UnidentifiedImageError
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
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_IMAGE_PIXELS = 25_000_000


@lru_cache(maxsize=1)
def _get_upload_worker():
    """Create one inference pipeline per API process for uploaded images."""
    worker_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "inference-worker")
    )
    if worker_dir not in sys.path:
        sys.path.insert(0, worker_dir)

    from worker import InferenceWorker

    return InferenceWorker()


@router.post("/upload-image", status_code=status.HTTP_200_OK, summary="Detect a Violation from an Uploaded Image")
async def upload_violation_image(
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Detect traffic violations in an uploaded image and issue a challan."""
    if image.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(status_code=415, detail="Upload a JPEG, PNG, or WEBP image.")

    image_bytes = await image.read(MAX_UPLOAD_BYTES + 1)
    if not image_bytes:
        raise HTTPException(status_code=400, detail="The uploaded image is empty.")
    if len(image_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Image must be 10 MB or smaller.")

    try:
        with Image.open(io.BytesIO(image_bytes)) as uploaded:
            if uploaded.width * uploaded.height > MAX_IMAGE_PIXELS:
                raise HTTPException(status_code=413, detail="Image dimensions are too large.")
            rgb_image = uploaded.convert("RGB")
            rgb_image.load()
    except (UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(status_code=400, detail="The uploaded file is not a valid image.")

    import numpy as np

    # Ultralytics expects an OpenCV-style BGR image array.
    frame = np.asarray(rgb_image)[:, :, ::-1].copy()
    worker = _get_upload_worker()
    event_id = f"evt_upload_{uuid.uuid4().hex}"
    detection = worker.detector.detect_frame(frame_np=frame, seed_hint=event_id)
    violations = detection.get("violations", [])
    if not violations:
        return {
            "status": "no_violation",
            "message": "No supported traffic violation was detected in this image.",
            "detected_objects": detection.get("boxes", []),
            "detection_mode": "simulated_fallback" if detection.get("is_fallback") else "yolo",
        }

    selected_violation = max(violations, key=lambda item: item.get("confidence", 0.0))
    now = datetime.now(timezone.utc)
    evidence_name = f"{event_id}.jpg"
    evidence_dir = os.path.join(settings.LOCAL_STORAGE_DIR, "frames", "uploads")
    os.makedirs(evidence_dir, exist_ok=True)
    evidence_path = os.path.join(evidence_dir, evidence_name)
    rgb_image.save(evidence_path, format="JPEG", quality=90)

    raw_plate = None
    plate_box = next(
        (
            box for box in detection.get("boxes", [])
            if box.get("class", "").lower().replace(" ", "_") in {"number_plate", "license_plate"}
        ),
        None,
    )
    if plate_box:
        x1, y1, x2, y2 = [int(value) for value in plate_box.get("bbox", [])]
        x1, x2 = max(0, x1), min(rgb_image.width, x2)
        y1, y2 = max(0, y1), min(rgb_image.height, y2)
        if x2 > x1 and y2 > y1:
            crop_buffer = io.BytesIO()
            rgb_image.crop((x1, y1, x2, y2)).save(crop_buffer, format="JPEG")
            plate, _, valid_plate = worker.ocr_engine.extract_plate(
                crop_bytes=crop_buffer.getvalue(), seed_hint=event_id
            )
            if valid_plate:
                raw_plate = plate

    event = {
        "event_id": event_id,
        "camera_id": "CAM-UPLOAD-01",
        "location_name": "Uploaded Image Review",
        "zone_id": "ZONE-CENTRAL-01",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "timestamp": now.isoformat(),
        "violation_type": selected_violation["type"],
        "confidence": selected_violation.get("confidence", 0.0),
        "raw_plate_text": raw_plate,
        "detected_objects": detection.get("boxes", []),
        "raw_frame_url": f"/artifacts/frames/uploads/{evidence_name}",
    }

    try:
        result = worker.process_event_payload(db, event)
    except Exception:
        db.rollback()
        logger.exception("Failed to process uploaded violation image")
        raise HTTPException(status_code=500, detail="Image was detected, but challan processing failed.")

    return {
        "status": "processed",
        "result": result,
        "detected_objects": detection.get("boxes", []),
        "detection_mode": "simulated_fallback" if detection.get("is_fallback") else "yolo",
        "evidence_url": event["raw_frame_url"],
    }

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
