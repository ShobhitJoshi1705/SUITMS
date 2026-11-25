from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, date
from typing import List
from services.common.models import Violation, Challan, CitizenReport, HotspotZone, ChallanStatus, HazardStatus
from services.common.schemas import AnalyticsSummary, HotspotResponse
from services.api.dependencies import get_db

router = APIRouter(prefix="/analytics", tags=["Analytics & Hotspots"])

@router.get("/summary", response_model=AnalyticsSummary, summary="Dashboard KPI Summary")
def get_analytics_summary(db: Session = Depends(get_db)):
    """Computes real-time KPI counters, revenue, and distribution breakdown for authority dashboard."""
    today_start = datetime.combine(date.today(), datetime.min.time())
    
    total_violations_today = db.query(Violation).filter(Violation.created_at >= today_start).count()
    active_challans = db.query(Challan).filter(Challan.status == ChallanStatus.ISSUED.value).count()
    
    # Financial metrics
    paid_fines = db.query(func.sum(Challan.fine_amount)).filter(Challan.status == ChallanStatus.PAID.value).scalar() or 0.0
    pending_fines = db.query(func.sum(Challan.fine_amount)).filter(Challan.status == ChallanStatus.ISSUED.value).scalar() or 0.0
    
    # Civic reports
    open_hazards = db.query(CitizenReport).filter(CitizenReport.status.in_([HazardStatus.REPORTED.value, HazardStatus.IN_REVIEW.value, HazardStatus.DISPATCHED.value])).count()
    resolved_hazards = db.query(CitizenReport).filter(CitizenReport.status == HazardStatus.RESOLVED.value).count()
    
    # Hotspots
    hotspots = db.query(HotspotZone).all()
    
    # Groupings
    v_by_type = {}
    for v_type, cnt in db.query(Violation.violation_type, func.count(Violation.id)).group_by(Violation.violation_type).all():
        v_by_type[v_type] = cnt
        
    h_by_cat = {}
    for cat, cnt in db.query(CitizenReport.category, func.count(CitizenReport.id)).group_by(CitizenReport.category).all():
        h_by_cat[cat] = cnt

    return AnalyticsSummary(
        total_violations_today=total_violations_today,
        active_challans_count=active_challans,
        total_fines_collected=float(paid_fines),
        pending_fines_amount=float(pending_fines),
        open_hazards_count=open_hazards,
        resolved_hazards_count=resolved_hazards,
        hotspots=[HotspotResponse.model_validate(h) for h in hotspots],
        violations_by_type=v_by_type,
        hazards_by_category=h_by_cat
    )

@router.get("/hotspots", response_model=List[HotspotResponse], summary="Hotspot Zones & Risk Levels")
def list_hotspots(db: Session = Depends(get_db)):
    """Returns all geographic urban traffic & hazard hotspots with computed risk scores."""
    return db.query(HotspotZone).order_by(HotspotZone.risk_level.desc()).all()
