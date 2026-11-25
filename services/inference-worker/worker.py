import time
import json
import logging
import datetime
from typing import Dict, Any, Optional
import redis
from sqlalchemy.orm import Session
from services.common.config import settings
from services.common.database import SessionLocal, init_db
from services.common.models import Violation, Challan, HotspotZone, ViolationStatus
from services.common.circuit_breaker import CircuitBreaker
from services.common.observability import metrics

# Import from local pipeline package
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from pipeline.detector import TrafficDetector
from pipeline.alpr_ocr import ALPROCREngine
from pipeline.hazard_detector import HazardDetector
from pipeline.challan_generator import ChallanGenerator

logger = logging.getLogger("suitms.worker")

class InferenceWorker:
    """
    Decoupled Asynchronous Processing Worker.
    Consumes detection events from Redis Stream, executes ALPR, plate normalization,
    rule verification, and idempotent Challan ticket generation.
    """
    def __init__(self):
        self.detector = TrafficDetector()
        self.ocr_engine = ALPROCREngine()
        self.hazard_engine = HazardDetector()
        self.redis_client = None
        self.circuit_breaker = CircuitBreaker("redis-worker", failure_threshold=3, recovery_time_seconds=5.0)
        self._init_redis()

    def _init_redis(self):
        try:
            self.redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD,
                db=settings.REDIS_DB,
                decode_responses=True
            )
            self.redis_client.ping()
            logger.info(f"Connected to Redis at {settings.REDIS_HOST}:{settings.REDIS_PORT}")
            # Ensure consumer group exists
            try:
                self.redis_client.xgroup_create(
                    settings.REDIS_STREAM_VIOLATIONS,
                    settings.REDIS_CONSUMER_GROUP,
                    id="0",
                    mkstream=True
                )
            except redis.exceptions.ResponseError as e:
                if "BUSYGROUP" not in str(e):
                    raise
        except Exception as e:
            logger.warning(f"Redis not available ({e}). Running in standalone/embedded mode.")

    def process_event_payload(self, db: Session, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Executes end-to-end ALPR, violation evaluation, and idempotent Challan creation.
        """
        start_time = time.time()
        camera_id = payload.get("camera_id", "CAM-UNKNOWN")
        location_name = payload.get("location_name", "City Junction")
        zone_id = payload.get("zone_id", "ZONE-CENTRAL-01")
        now = datetime.datetime.utcnow()

        # Step 1: Extract & Normalize License Plate
        raw_plate = payload.get("raw_plate_text")
        seed_hint = payload.get("event_id") or f"{camera_id}_{time.time()}"
        plate_number, ocr_conf, is_valid_plate = self.ocr_engine.extract_plate(seed_hint=seed_hint)
        if raw_plate:
            plate_number = raw_plate

        # Step 2: Detect Violations
        violation_type = payload.get("violation_type")
        confidence = float(payload.get("confidence", 0.92))
        if not violation_type:
            det_result = self.detector.detect_frame(seed_hint=seed_hint)
            violations = det_result.get("violations", [])
            if violations:
                violation_type = violations[0]["type"]
                confidence = violations[0]["confidence"]
            else:
                violation_type = "NO_HELMET"

        # Step 3: Compute Idempotency Key
        idempotency_key = ChallanGenerator.compute_idempotency_key(
            camera_id=camera_id,
            plate_number=plate_number,
            violation_type=violation_type,
            timestamp=now
        )

        # Step 4: Check if Violation / Challan already exists (Idempotency guarantee)
        existing_violation = db.query(Violation).filter(Violation.idempotency_key == idempotency_key).first()
        if existing_violation:
            logger.info(f"Duplicate violation event skipped for idempotency_key={idempotency_key}")
            return {"status": "duplicate_skipped", "idempotency_key": idempotency_key}

        # Step 5: Save Violation
        violation = Violation(
            idempotency_key=idempotency_key,
            camera_id=camera_id,
            location_name=location_name,
            zone_id=zone_id,
            latitude=payload.get("latitude", 12.9716),
            longitude=payload.get("longitude", 77.5946),
            violation_type=violation_type,
            confidence=confidence,
            plate_number=plate_number,
            raw_frame_url=payload.get("raw_frame_url", f"/artifacts/frames/{camera_id}_{now.strftime('%H%M%S')}.jpg"),
            crop_url=payload.get("crop_url", f"/artifacts/crops/{plate_number}.jpg"),
            status=ViolationStatus.CHALLAN_ISSUED.value,
            metadata_json=json.dumps(payload.get("detected_objects", [])),
            created_at=now
        )
        db.add(violation)
        db.flush()

        # Step 6: Generate Automated Idempotent Challan
        challan = ChallanGenerator.create_challan(violation)
        db.add(challan)

        # Step 7: Update Hotspot Count
        hotspot = db.query(HotspotZone).filter(HotspotZone.zone_id == zone_id).first()
        if hotspot:
            hotspot.violation_count += 1
            if hotspot.violation_count > 25:
                hotspot.risk_level = "SEVERE"
            elif hotspot.violation_count > 15:
                hotspot.risk_level = "HIGH"
            elif hotspot.violation_count > 5:
                hotspot.risk_level = "MEDIUM"

        db.commit()

        # Step 8: Metrics & Event Broadcast
        duration = time.time() - start_time
        metrics.record_inference(duration)
        metrics.record_violation(violation_type)
        metrics.record_challan()

        event_data = {
            "type": "NEW_VIOLATION_CHALLAN",
            "violation_id": violation.id,
            "challan_number": challan.challan_number,
            "plate_number": plate_number,
            "violation_type": violation_type,
            "fine_amount": challan.fine_amount,
            "location": location_name,
            "zone_id": zone_id,
            "timestamp": now.isoformat()
        }

        # Broadcast via Redis Pub/Sub if connected
        if self.redis_client:
            try:
                self.redis_client.publish("events:broadcast", json.dumps(event_data))
            except Exception as e:
                logger.warning(f"Failed to publish event to Redis: {e}")

        logger.info(f"Generated Challan {challan.challan_number} for {plate_number} ({violation_type}) in {duration:.3f}s")
        return event_data

    def run_consumer_loop(self):
        """Infinite loop consuming stream events from Redis."""
        logger.info("Starting Redis Stream consumer loop...")
        init_db()
        while True:
            if not self.redis_client:
                time.sleep(2)
                self._init_redis()
                continue
            
            try:
                entries = self.redis_client.xreadgroup(
                    groupname=settings.REDIS_CONSUMER_GROUP,
                    consumername="worker-1",
                    streams={settings.REDIS_STREAM_VIOLATIONS: ">"},
                    count=5,
                    block=2000
                )
                if entries:
                    db = SessionLocal()
                    try:
                        for stream_name, msg_list in entries:
                            metrics.set_queue_depth(len(msg_list))
                            for msg_id, data in msg_list:
                                payload = json.loads(data.get("payload", "{}"))
                                self.process_event_payload(db, payload)
                                self.redis_client.xack(settings.REDIS_STREAM_VIOLATIONS, settings.REDIS_CONSUMER_GROUP, msg_id)
                    finally:
                        db.close()
            except Exception as e:
                logger.error(f"Consumer loop error: {e}")
                time.sleep(1)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    worker = InferenceWorker()
    worker.run_consumer_loop()
