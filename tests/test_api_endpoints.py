import pytest
import os
import sys
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.api.main import app
from services.common.database import init_db

# Initialize database schema for test run
init_db()

client = TestClient(app)

def test_liveness():
    res = client.get("/health/live")
    assert res.status_code == 200
    assert res.json()["status"] == "alive"

def test_readiness():
    res = client.get("/health/ready")
    assert res.status_code in [200, 503]
    data = res.json()
    assert "components" in data

def test_prometheus_metrics():
    res = client.get("/metrics")
    assert res.status_code == 200
    assert "suitms_http_requests_total" in res.text

def test_citizen_report_submission_and_tracking():
    idemp_key = "TEST-REPORT-IDEMP-001"
    payload = {
        "category": "POTHOLE",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "address": "MG Road near Metro Station",
        "zone_id": "ZONE-CENTRAL-01",
        "description": "Hazardous road crater causing traffic bottleneck",
        "reporter_contact": "citizen@example.com"
    }

    # First submission
    res1 = client.post("/api/v1/citizen-reports", json=payload, headers={"Idempotency-Key": idemp_key})
    assert res1.status_code == 201
    ticket_id = res1.json()["ticket_id"]
    assert ticket_id.startswith("HAZ-")

    # Idempotent retry: must return exact same ticket without duplicate
    res2 = client.post("/api/v1/citizen-reports", json=payload, headers={"Idempotency-Key": idemp_key})
    assert res2.status_code == 201
    assert res2.json()["ticket_id"] == ticket_id

    # Lookup by ticket ID
    res3 = client.get(f"/api/v1/citizen-reports/{ticket_id}")
    assert res3.status_code == 200
    assert res3.json()["ticket_id"] == ticket_id
    assert res3.json()["category"] == "POTHOLE"
