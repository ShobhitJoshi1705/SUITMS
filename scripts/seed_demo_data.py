import sys
import os
import datetime
import random

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "services", "inference-worker")))

from services.common.database import SessionLocal, init_db
from services.common.models import Violation, Challan, CitizenReport, HotspotZone, ViolationStatus, ChallanStatus, HazardStatus, HazardPriority
from pipeline.challan_generator import ChallanGenerator

def seed_database():
    print("Initializing schema...")
    init_db()
    db = SessionLocal()

    try:
        now = datetime.datetime.utcnow()
        cameras = [
            ("CAM-MG-ROAD-01", "MG Road & Central Plaza", "ZONE-CENTRAL-01", 12.9716, 77.5946),
            ("CAM-NORTH-02", "Outer Ring Road Interchange", "ZONE-NORTH-02", 13.0358, 77.5970),
            ("CAM-EAST-03", "IT Corridor Express Flyover", "ZONE-EAST-03", 12.9352, 77.6245),
            ("CAM-SOUTH-04", "Market Square Bus Terminal", "ZONE-SOUTH-04", 12.9250, 77.5838),
        ]

        plates = [
            "KA01AB1234", "DL03C9876", "MH12DE4321", "TN09XY5678",
            "KA05MN8899", "UP14ZZ1122", "TS07JK3344", "KA03EF7766"
        ]

        violations_pool = ["NO_HELMET", "TRIPLE_RIDING", "SPEEDING", "RED_LIGHT"]

        print("Seeding sample traffic violations & automated Challans...")
        for i, plate in enumerate(plates):
            cam = random.choice(cameras)
            v_type = random.choice(violations_pool)
            event_time = now - datetime.timedelta(minutes=random.randint(5, 300))
            
            idemp_key = ChallanGenerator.compute_idempotency_key(
                cam[0], plate, v_type, event_time
            )
            
            # Check existing
            if db.query(Violation).filter(Violation.idempotency_key == idemp_key).first():
                continue

            v = Violation(
                idempotency_key=idemp_key,
                camera_id=cam[0],
                location_name=cam[1],
                zone_id=cam[2],
                latitude=cam[3],
                longitude=cam[4],
                violation_type=v_type,
                confidence=round(random.uniform(0.91, 0.98), 2),
                plate_number=plate,
                raw_frame_url=f"/artifacts/frames/{cam[0]}_{i}.jpg",
                crop_url=f"/artifacts/crops/{plate}.jpg",
                status=ViolationStatus.CHALLAN_ISSUED.value,
                created_at=event_time
            )
            db.add(v)
            db.flush()

            challan = ChallanGenerator.create_challan(v)
            if i % 3 == 0:
                challan.status = ChallanStatus.PAID.value
                challan.paid_at = now - datetime.timedelta(minutes=10)
            db.add(challan)

        print("Seeding sample citizen civic hazard reports...")
        hazards = [
            ("POTHOLE", 12.9720, 77.5950, "MG Road near Trinity Metro", "ZONE-CENTRAL-01", "Large crater on right lane causing 2-wheeler skids", HazardStatus.REPORTED.value, HazardPriority.HIGH.value),
            ("BROKEN_BARRIER", 13.0360, 77.5975, "Outer Ring Road Exit 3", "ZONE-NORTH-02", "Damaged metal crash barrier following collision", HazardStatus.IN_REVIEW.value, HazardPriority.HIGH.value),
            ("GARBAGE_DUMP", 12.9360, 77.6250, "IT Corridor Service Road", "ZONE-EAST-03", "Construction debris blocking pedestrian sidewalk", HazardStatus.DISPATCHED.value, HazardPriority.MEDIUM.value),
            ("WATERLOGGING", 12.9255, 77.5840, "Market Square Underpass", "ZONE-SOUTH-04", "Severe drainage overflow, 2 feet water depth", HazardStatus.RESOLVED.value, HazardPriority.CRITICAL.value),
        ]

        for cat, lat, lon, addr, zone, desc, st, prio in hazards:
            ticket = f"HAZ-2026-{random.randint(1000, 9999)}"
            idemp = f"SEED:{ticket}"
            if db.query(CitizenReport).filter(CitizenReport.idempotency_key == idemp).first():
                continue
            rep = CitizenReport(
                ticket_id=ticket,
                idempotency_key=idemp,
                category=cat,
                latitude=lat,
                longitude=lon,
                address=addr,
                zone_id=zone,
                description=desc,
                status=st,
                priority=prio,
                created_at=now - datetime.timedelta(hours=random.randint(1, 48))
            )
            db.add(rep)

        db.commit()
        print("Demo data seeded successfully into SQLite / PostgreSQL!")
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
