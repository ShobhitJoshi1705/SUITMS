import pytest
import os
import sys
import shutil

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, root_dir)
sys.path.insert(0, os.path.join(root_dir, "services", "edge-simulator"))

from spooler import DiskSpooler

TEST_SPOOL_DIR = "./test_edge_spool"

@pytest.fixture(autouse=True)
def cleanup_spool():
    if os.path.exists(TEST_SPOOL_DIR):
        shutil.rmtree(TEST_SPOOL_DIR)
    yield
    if os.path.exists(TEST_SPOOL_DIR):
        shutil.rmtree(TEST_SPOOL_DIR)

def test_disk_spooler_persists_offline_events():
    spooler = DiskSpooler(spool_dir=TEST_SPOOL_DIR)
    event1 = {"event_id": "evt_1", "camera_id": "CAM-01", "plate": "KA01AB1111"}
    event2 = {"event_id": "evt_2", "camera_id": "CAM-02", "plate": "KA01AB2222"}

    # Simulate offline network (always returning False)
    delivered = spooler.dispatch_or_spool(event1, send_func=lambda x: False)
    assert delivered is False
    assert spooler.get_spool_depth() == 1

    delivered2 = spooler.dispatch_or_spool(event2, send_func=lambda x: False)
    assert delivered2 is False
    assert spooler.get_spool_depth() == 2

    # Verify draining/replay upon network restoration
    replayed_events = []
    def mock_online_send(evt):
        replayed_events.append(evt)
        return True

    flushed = spooler.flush_spooled(mock_online_send)
    assert flushed == 2
    assert spooler.get_spool_depth() == 0
    assert len(replayed_events) == 2
    assert replayed_events[0]["event_id"] == "evt_1"
    assert replayed_events[1]["event_id"] == "evt_2"

def test_backoff_calculation():
    spooler = DiskSpooler(spool_dir=TEST_SPOOL_DIR, base_backoff_sec=1.0, max_backoff_sec=10.0)
    spooler.consecutive_failures = 0
    b0 = spooler.compute_backoff()
    assert 0.5 <= b0 <= 2.0

    spooler.consecutive_failures = 3
    b3 = spooler.compute_backoff()
    assert 5.0 <= b3 <= 12.0
