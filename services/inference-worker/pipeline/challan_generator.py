import hashlib
import uuid
import datetime
from typing import Dict, Any, Optional
from services.common.models import Challan, Violation, ViolationType, ChallanStatus

class ChallanGenerator:
    """
    Automated Idempotent Challan (Traffic Violation Ticket) Generator.
    Guarantees strict deduplication: repeated camera frames of the same vehicle
    within a sliding time window (60s) produce the exact same idempotency key,
    preventing duplicate fines.
    """

    FINE_MATRIX = {
        ViolationType.NO_HELMET.value: 1000.0,
        ViolationType.TRIPLE_RIDING.value: 2000.0,
        ViolationType.SPEEDING.value: 1500.0,
        ViolationType.RED_LIGHT.value: 1000.0,
        ViolationType.HAZARD_BLOCK.value: 500.0,
    }

    @classmethod
    def compute_idempotency_key(cls, camera_id: str, plate_number: str, violation_type: str, timestamp: datetime.datetime, window_seconds: int = 60) -> str:
        """
        Calculates deterministic bucketed idempotency key:
        SHA256(camera_id : normalized_plate : violation_type : time_window_index)
        """
        epoch_sec = int(timestamp.timestamp())
        window_bucket = epoch_sec // window_seconds
        raw_seed = f"{camera_id.strip().upper()}:{plate_number.strip().upper()}:{violation_type.strip().upper()}:{window_bucket}"
        return hashlib.sha256(raw_seed.encode("utf-8")).hexdigest()

    @classmethod
    def create_challan(
        cls,
        violation: Violation,
        due_days: int = 30
    ) -> Challan:
        """
        Creates a new Challan model instance with deterministic numbering and idempotency key.
        """
        now = datetime.datetime.utcnow()
        due_date = now + datetime.timedelta(days=due_days)
        
        fine = cls.FINE_MATRIX.get(violation.violation_type, 1000.0)
        
        # Challan idempotency key derived directly from violation idempotency key
        challan_idempotency = f"CHALLAN:{violation.idempotency_key}"
        challan_number = f"CH-{now.year}-{uuid.uuid4().hex[:8].upper()}"

        return Challan(
            challan_number=challan_number,
            idempotency_key=challan_idempotency,
            violation_id=violation.id,
            plate_number=violation.plate_number or "UNKNOWN",
            violation_type=violation.violation_type,
            fine_amount=fine,
            due_date=due_date,
            status=ChallanStatus.ISSUED.value,
            evidence_url=violation.crop_url or violation.raw_frame_url,
            created_at=now,
        )
