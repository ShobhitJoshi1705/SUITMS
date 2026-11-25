import time
import logging
import json
import uuid
from typing import Dict, Any
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Configure structured JSON logging format
class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_obj: Dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "request_id"):
            log_obj["request_id"] = getattr(record, "request_id")
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj)

def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    logger.handlers = [handler]

# Prometheus Metrics Collector (In-memory, exposes standard Prometheus text format)
class MetricsRegistry:
    def __init__(self):
        self.http_requests_total: Dict[str, int] = {}
        self.http_request_duration_seconds: Dict[str, float] = {}
        self.violations_detected_total: Dict[str, int] = {}
        self.challans_generated_total: int = 0
        self.inference_duration_seconds: float = 0.0
        self.inference_count: int = 0
        self.queue_depth: int = 0
        self.circuit_breaker_trips: int = 0

    def record_http_request(self, method: str, path: str, status_code: int, duration: float):
        key = f'{method}:{path}:{status_code}'
        self.http_requests_total[key] = self.http_requests_total.get(key, 0) + 1
        self.http_request_duration_seconds[key] = duration

    def record_violation(self, violation_type: str):
        self.violations_detected_total[violation_type] = self.violations_detected_total.get(violation_type, 0) + 1

    def record_challan(self):
        self.challans_generated_total += 1

    def record_inference(self, duration: float):
        self.inference_count += 1
        self.inference_duration_seconds += duration

    def set_queue_depth(self, depth: int):
        self.queue_depth = depth

    def generate_prometheus_output(self) -> str:
        lines = []
        lines.append("# HELP suitms_http_requests_total Total HTTP requests")
        lines.append("# TYPE suitms_http_requests_total counter")
        for key, val in self.http_requests_total.items():
            parts = key.split(":")
            lines.append(f'suitms_http_requests_total{{method="{parts[0]}",endpoint="{parts[1]}",status="{parts[2]}"}} {val}')
            
        lines.append("# HELP suitms_violations_total Total traffic violations detected")
        lines.append("# TYPE suitms_violations_total counter")
        for v_type, val in self.violations_detected_total.items():
            lines.append(f'suitms_violations_total{{type="{v_type}"}} {val}')

        lines.append("# HELP suitms_challans_total Total automated challans issued")
        lines.append("# TYPE suitms_challans_total counter")
        lines.append(f"suitms_challans_total {self.challans_generated_total}")

        lines.append("# HELP suitms_inference_latency_avg_seconds Average ML inference latency")
        lines.append("# TYPE suitms_inference_latency_avg_seconds gauge")
        avg_inf = (self.inference_duration_seconds / max(1, self.inference_count))
        lines.append(f"suitms_inference_latency_avg_seconds {avg_inf:.4f}")

        lines.append("# HELP suitms_queue_depth Pending message queue backlog depth")
        lines.append("# TYPE suitms_queue_depth gauge")
        lines.append(f"suitms_queue_depth {self.queue_depth}")

        return "\n".join(lines) + "\n"

metrics = MetricsRegistry()

class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        req_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = req_id
        
        start_time = time.time()
        response: Response = await call_next(request)
        duration = time.time() - start_time
        
        response.headers["X-Request-ID"] = req_id
        metrics.record_http_request(request.method, request.url.path, response.status_code, duration)
        return response
