import pytest
import datetime
import os
import sys

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, root_dir)
sys.path.insert(0, os.path.join(root_dir, "services", "inference-worker"))

from pipeline.challan_generator import ChallanGenerator
from services.common.models import Violation, Challan, ViolationType
from services.common.database import SessionLocal, init_db

def test_idempotency_key_deterministic():
    t1 = datetime.datetime(2026, 11, 21, 10, 0, 15)
    t2 = datetime.datetime(2026, 11, 21, 10, 0, 45) # Same 60s bucket
    t3 = datetime.datetime(2026, 11, 21, 10, 1, 15) # Next 60s bucket

    key1 = ChallanGenerator.compute_idempotency_key("CAM-01", "KA01AB1234", "NO_HELMET", t1)
    key2 = ChallanGenerator.compute_idempotency_key("CAM-01", "KA01AB1234", "NO_HELMET", t2)
    key3 = ChallanGenerator.compute_idempotency_key("CAM-01", "KA01AB1234", "NO_HELMET", t3)

    # Identical camera, plate, violation within same 60-second window must yield exact same key
    assert key1 == key2
    # Different time window must yield distinct key
    assert key1 != key3

def test_challan_generation_attributes():
    v = Violation(
        id="test-v-id-123",
        idempotency_key="TEST-IDEMP-KEY-999",
        camera_id="CAM-MG-ROAD-01",
        location_name="MG Road",
        zone_id="ZONE-CENTRAL-01",
        violation_type=ViolationType.TRIPLE_RIDING.value,
        plate_number="KA01AB1234",
    )
    challan = ChallanGenerator.create_challan(v)
    assert challan.fine_amount == 2000.0 # Triple riding fine
    assert challan.violation_type == ViolationType.TRIPLE_RIDING.value
    assert challan.idempotency_key == f"CHALLAN:{v.idempotency_key}"
    assert challan.challan_number.startswith("CH-")
    assert challan.status == "ISSUED"
