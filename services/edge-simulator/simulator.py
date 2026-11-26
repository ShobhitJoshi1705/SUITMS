import time
import json
import uuid
import random
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import httpx
from services.common.config import settings
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from spooler import DiskSpooler

logger = logging.getLogger("suitms.edge_simulator")

class EdgeCameraSimulator:
    """
    Simulates high-throughput edge nodes (e.g. NVIDIA Jetson deployed at traffic junctions).
    Performs edge pre-filtering, plate localization, and streaming to API/Redis
    with resilient disk ring-buffer spooling.
    """
    CAMERAS = [
        {"camera_id": "CAM-MG-ROAD-01", "location_name": "MG Road Junction", "zone_id": "ZONE-CENTRAL-01", "lat": 12.9716, "lon": 77.5946},
        {"camera_id": "CAM-RING-ROAD-02", "location_name": "Outer Ring Road Exit 4", "zone_id": "ZONE-NORTH-02", "lat": 13.0358, "lon": 77.5970},
        {"camera_id": "CAM-IT-EXPRESS-03", "location_name": "IT Expressway Flyover", "zone_id": "ZONE-EAST-03", "lat": 12.9352, "lon": 77.6245},
        {"camera_id": "CAM-MARKET-04", "location_name": "Central Market Bus Terminal", "zone_id": "ZONE-SOUTH-04", "lat": 12.9250, "lon": 77.5838},
    ]

    VIOLATION_TYPES = ["NO_HELMET", "TRIPLE_RIDING", "SPEEDING", "RED_LIGHT"]

    def __init__(self, api_base_url: Optional[str] = None):
        self.api_url = (
            api_base_url
            or os.getenv("API_INGEST_URL")
            or f"http://localhost:{settings.PORT}{settings.API_V1_PREFIX}/violations/ingest"
        )
        self.spooler = DiskSpooler(spool_dir=settings.SPOOL_DIR)
        self.http_client = httpx.Client(timeout=3.0)

    def generate_synthetic_event(self) -> Dict[str, Any]:
        """Generates a realistic traffic violation or road hazard event."""
        cam = random.choice(self.CAMERAS)
        event_id = f"evt_{uuid.uuid4().hex[:12]}"
        v_type = random.choice(self.VIOLATION_TYPES)
        
        # Plate format: KA01AB1234
        state = random.choice(["KA", "DL", "MH", "TN", "UP", "TS"])
        dist = f"{random.randint(1, 99):02d}"
        series = random.choice(["AB", "CD", "EF", "GH", "JK", "XY"])
        num = f"{random.randint(1000, 9999)}"
        plate = f"{state}{dist}{series}{num}"

        payload = {
            "event_id": event_id,
            "camera_id": cam["camera_id"],
            "location_name": cam["location_name"],
            "zone_id": cam["zone_id"],
            "latitude": cam["lat"],
            "longitude": cam["lon"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "violation_type": v_type,
            "confidence": round(random.uniform(0.88, 0.99), 2),
            "raw_plate_text": plate,
            "detected_objects": [
                {"class": "bike", "bbox": [100, 200, 450, 600]},
                {"class": "rider", "bbox": [150, 100, 380, 500]},
                {"class": "number_plate", "bbox": [220, 520, 320, 570]}
            ]
        }
        return payload

    def send_to_backend(self, event: Dict[str, Any]) -> bool:
        """Sends payload over HTTP to FastAPI central ingestion endpoint."""
        try:
            # Older spool files may contain epoch timestamps. The API schema
            # expects an ISO timestamp string, so normalize those during replay.
            payload = dict(event)
            timestamp = payload.get("timestamp")
            if isinstance(timestamp, (int, float)):
                payload["timestamp"] = datetime.fromtimestamp(
                    timestamp, tz=timezone.utc
                ).isoformat()

            resp = self.http_client.post(self.api_url, json=payload)
            if resp.is_error:
                logger.warning(
                    "Backend rejected event with HTTP %s: %s",
                    resp.status_code,
                    resp.text[:500],
                )
            return resp.status_code in [200, 201, 202]
        except Exception as e:
            logger.warning(f"Transmission to backend failed: {e}")
            return False

    def emit_event(self) -> bool:
        """Generates and delivers or spools a single detection event."""
        event = self.generate_synthetic_event()
        return self.spooler.dispatch_or_spool(event, self.send_to_backend)

    def run_continuous_simulation(self, interval_sec: float = 3.0, max_events: Optional[int] = None):
        """Runs continuous edge camera streaming loop."""
        logger.info(f"Edge Camera Simulator started. Streaming to {self.api_url}")
        count = 0
        try:
            while max_events is None or count < max_events:
                self.emit_event()
                count += 1
                time.sleep(interval_sec)
        except KeyboardInterrupt:
            logger.info("Simulation halted by user.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sim = EdgeCameraSimulator()
    sim.run_continuous_simulation(interval_sec=2.0)
