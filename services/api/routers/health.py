from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from services.common.config import settings
from services.common.observability import metrics
from services.api.dependencies import get_db, get_redis_client

router = APIRouter(tags=["Health & Observability"])

@router.get("/health/live", summary="Kubernetes / Nginx Liveness Probe")
def liveness():
    """Returns 200 OK if the process is alive."""
    return {"status": "alive", "service": "suitms-api", "version": settings.VERSION}

@router.get("/health/ready", summary="Active Readiness Probe with Dependency Health")
def readiness(response: Response, db: Session = Depends(get_db)):
    """
    Checks connectivity to database and Redis.
    Fails with 503 if critical dependencies are down so Nginx can divert traffic.
    """
    db_healthy = False
    redis_healthy = False
    details = {}

    # Check Database
    try:
        db.execute(text("SELECT 1"))
        db_healthy = True
        details["database"] = "UP"
    except Exception as e:
        details["database"] = f"DOWN ({str(e)})"

    # Check Redis
    r_client = get_redis_client()
    if r_client:
        try:
            r_client.ping()
            redis_healthy = True
            details["redis"] = "UP"
        except Exception as e:
            details["redis"] = f"DOWN ({str(e)})"
    else:
        details["redis"] = "DEGRADED (Circuit Open / Fallback Active)"

    # Determine readiness
    if not db_healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "UNREADY", "ready": False, "components": details}

    return {"status": "READY", "ready": True, "components": details}

@router.get("/metrics", summary="Prometheus Metrics Scrape Endpoint")
def get_metrics():
    """Exposes application and pipeline metrics in standard Prometheus exposition format."""
    output = metrics.generate_prometheus_output()
    return Response(content=output, media_type="text/plain; version=0.0.4; charset=utf-8")
