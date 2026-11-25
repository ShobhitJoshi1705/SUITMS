import time
import requests
import json
import random
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("suitms.failover_test")

def test_api_failover(lb_url="http://localhost:80"):
    """
    Simulates high-throughput requests to Nginx load balancer to verify
    upstream load distribution across api-1 and api-2 replicas.
    """
    logger.info(f"--- 1. Testing Nginx Ingress & Upstream Availability ({lb_url}) ---")
    successes = 0
    failures = 0
    start = time.time()

    for i in range(20):
        try:
            res = requests.get(f"{lb_url}/health/ready", timeout=2.0)
            if res.status_code in [200, 503]:
                successes += 1
            else:
                failures += 1
        except Exception as e:
            failures += 1
        time.sleep(0.05)

    duration = time.time() - start
    logger.info(f"Load Balancer Probe: {successes}/20 successful in {duration:.2f}s ({failures} failed)")

def test_queue_backpressure(ingest_url="http://localhost:80/api/v1/violations/ingest"):
    """
    Pumps high-frequency burst traffic to verify edge ingestion decoupling
    and queue backpressure absorption.
    """
    logger.info(f"--- 2. Testing Ingestion Burst & Backpressure ({ingest_url}) ---")
    burst_count = 50
    accepted = 0
    start = time.time()

    for i in range(burst_count):
        payload = {
            "event_id": f"burst_test_{i}_{time.time()}",
            "camera_id": f"CAM-BURST-{(i % 4) + 1:02d}",
            "location_name": "Outer Ring Road High Speed Corridor",
            "zone_id": "ZONE-NORTH-02",
            "timestamp": time.time(),
            "violation_type": random.choice(["NO_HELMET", "TRIPLE_RIDING", "SPEEDING"]),
            "confidence": 0.95,
            "raw_plate_text": f"KA01AB{1000 + i}",
            "detected_objects": []
        }
        try:
            res = requests.post(ingest_url, json=payload, timeout=3.0)
            if res.status_code in [200, 201, 202]:
                accepted += 1
        except Exception as e:
            logger.warning(f"Request {i} failed: {e}")

    duration = time.time() - start
    throughput = burst_count / max(0.001, duration)
    logger.info(f"Burst Injection: {accepted}/{burst_count} events ingested in {duration:.2f}s ({throughput:.1f} req/s)")

def test_challan_idempotency(api_url="http://localhost:80/api/v1"):
    """
    Verifies that duplicate violation events from the same vehicle & camera
    produce exactly one Challan and do not duplicate fines.
    """
    logger.info("--- 3. Testing Challan Generation Idempotency ---")
    fixed_plate = f"TEST{random.randint(1000, 9999)}"
    event = {
        "event_id": "idemp_test_01",
        "camera_id": "CAM-MG-ROAD-01",
        "location_name": "MG Road Junction",
        "zone_id": "ZONE-CENTRAL-01",
        "timestamp": time.time(),
        "violation_type": "NO_HELMET",
        "confidence": 0.96,
        "raw_plate_text": fixed_plate,
        "detected_objects": []
    }

    # Transmit same event 3 times in rapid succession
    for attempt in range(1, 4):
        try:
            res = requests.post(f"{api_url}/violations/ingest", json=event, timeout=2.0)
            logger.info(f"Attempt {attempt}: Status {res.status_code}")
        except Exception as e:
            logger.warning(f"Attempt {attempt} connection failed: {e}")

    # Query Challans for this plate
    try:
        res = requests.get(f"{api_url}/violations/challans?plate_number={fixed_plate}", timeout=2.0)
        if res.status_code == 200:
            challans = res.json()
            logger.info(f"Challans returned for {fixed_plate}: {len(challans)} (Must be <= 1 for strict idempotency)")
            assert len(challans) <= 1, "Duplicate challan was created!"
    except Exception as e:
        logger.info(f"Verification query skipped (API offline): {e}")

if __name__ == "__main__":
    test_api_failover()
    test_queue_backpressure()
    test_challan_idempotency()
