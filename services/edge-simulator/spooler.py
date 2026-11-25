import os
import json
import time
import random
import glob
import logging
from typing import Dict, Any, List, Optional, Callable

logger = logging.getLogger("suitms.spooler")

class DiskSpooler:
    """
    High-Availability Local Disk Ring-Buffer Spooler for Edge Nodes (e.g. NVIDIA Jetson).
    Provides resilient buffering during network WAN outages or central backend downtime.
    Features:
      - Bounded disk storage with ring-buffer FIFO retention
      - Exponential backoff with jitter ($T = min(T_max, T_base * 2^attempt) + jitter$)
      - Zero data loss: persists events locally and drains upon connection recovery
    """
    def __init__(
        self,
        spool_dir: str = "./edge_spool",
        max_spool_size_mb: int = 100,
        base_backoff_sec: float = 1.0,
        max_backoff_sec: float = 30.0,
        jitter_factor: float = 0.25
    ):
        self.spool_dir = os.path.abspath(spool_dir)
        self.max_spool_bytes = max_spool_size_mb * 1024 * 1024
        self.base_backoff = base_backoff_sec
        self.max_backoff = max_backoff_sec
        self.jitter_factor = jitter_factor
        
        self.consecutive_failures = 0
        os.makedirs(self.spool_dir, exist_ok=True)
        logger.info(f"DiskSpooler initialized at {self.spool_dir} (Max capacity: {max_spool_size_mb}MB)")

    def _get_current_spool_size(self) -> int:
        total = 0
        for entry in os.scandir(self.spool_dir):
            if entry.is_file() and entry.name.endswith(".json"):
                total += entry.stat().st_size
        return total

    def _enforce_ring_buffer_limit(self):
        """Drops oldest files if total disk space exceeds max capacity."""
        current_size = self._get_current_spool_size()
        if current_size <= self.max_spool_bytes:
            return

        files = sorted(glob.glob(os.path.join(self.spool_dir, "*.json")))
        for f in files:
            try:
                os.remove(f)
                logger.warning(f"Spool ring-buffer full! Pruned oldest spooled file: {os.path.basename(f)}")
                if self._get_current_spool_size() <= self.max_spool_bytes * 0.8:
                    break
            except OSError as e:
                logger.error(f"Failed to remove spooled file {f}: {e}")

    def spool_event(self, event: Dict[str, Any]) -> str:
        """Saves event payload to local disk spool file."""
        self._enforce_ring_buffer_limit()
        timestamp_ns = time.time_ns()
        event_id = event.get("event_id", "evt")
        filename = f"{timestamp_ns}_{event_id}.json"
        filepath = os.path.join(self.spool_dir, filename)
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(event, f)
            
        logger.warning(f"Network offline. Spooled event to disk: {filename}")
        return filepath

    def get_spool_depth(self) -> int:
        """Returns the number of events currently spooled on disk."""
        return len(glob.glob(os.path.join(self.spool_dir, "*.json")))

    def compute_backoff(self) -> float:
        """Calculates exponential backoff delay with random jitter."""
        backoff = min(self.max_backoff, self.base_backoff * (2 ** self.consecutive_failures))
        jitter = random.uniform(-self.jitter_factor, self.jitter_factor) * backoff
        return max(0.5, backoff + jitter)

    def dispatch_or_spool(
        self,
        event: Dict[str, Any],
        send_func: Callable[[Dict[str, Any]], bool]
    ) -> bool:
        """
        Attempts to deliver event via send_func.
        If network fails, spools to disk buffer and enters backoff state.
        """
        # If we have a backlog of spooled items, flush them first
        if self.get_spool_depth() > 0:
            self.flush_spooled(send_func)

        try:
            success = send_func(event)
            if success:
                self.consecutive_failures = 0
                return True
            else:
                self.consecutive_failures += 1
                self.spool_event(event)
                return False
        except Exception as e:
            self.consecutive_failures += 1
            logger.error(f"Dispatch error ({e}). Initiating spooling.")
            self.spool_event(event)
            return False

    def flush_spooled(self, send_func: Callable[[Dict[str, Any]], bool]) -> int:
        """
        Drains spooled files in strict FIFO order, sending each to the backend.
        Stops upon first transmission failure to preserve ordering.
        """
        files = sorted(glob.glob(os.path.join(self.spool_dir, "*.json")))
        flushed_count = 0
        
        for fpath in files:
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    event = json.load(f)
                    
                success = send_func(event)
                if success:
                    os.remove(fpath)
                    flushed_count += 1
                    self.consecutive_failures = 0
                    logger.info(f"Successfully replayed and drained spooled event: {os.path.basename(fpath)}")
                else:
                    self.consecutive_failures += 1
                    logger.warning(f"Replay halted: upstream backend unreachable.")
                    break
            except Exception as e:
                self.consecutive_failures += 1
                logger.error(f"Failed to replay spooled file {fpath}: {e}")
                break
                
        return flushed_count
