import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from services.common.config import settings
from services.common.database import init_db
from services.common.observability import setup_logging, CorrelationIdMiddleware
from services.api.routers import health, violations, citizen_reports, analytics, ws

# Initialize structured logging
setup_logging()
logger = logging.getLogger("suitms.api")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize DB schema & seed data
    logger.info("SUITMS API starting up...")
    init_db()
    
    # Ensure local storage directories exist
    os.makedirs(os.path.join(settings.LOCAL_STORAGE_DIR, "suitms-artifacts"), exist_ok=True)
    os.makedirs(os.path.join(settings.LOCAL_STORAGE_DIR, "suitms-hazards"), exist_ok=True)
    os.makedirs(os.path.join(settings.LOCAL_STORAGE_DIR, "crops"), exist_ok=True)
    os.makedirs(os.path.join(settings.LOCAL_STORAGE_DIR, "frames"), exist_ok=True)
    
    yield
    logger.info("SUITMS API shutting down gracefully...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Smart Urban Infrastructure & Traffic Management System (SUITMS) High-Availability API",
    lifespan=lifespan
)

# Correlation ID and Request Tracing Middleware
app.add_middleware(CorrelationIdMiddleware)

# Cross-Origin Resource Sharing (CORS)
origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if "*" not in origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Routers
app.include_router(health.router)
app.include_router(violations.router, prefix=settings.API_V1_PREFIX)
app.include_router(citizen_reports.router, prefix=settings.API_V1_PREFIX)
app.include_router(analytics.router, prefix=settings.API_V1_PREFIX)
app.include_router(ws.router)

# Mount local storage as static files for seamless artifact viewing
artifacts_dir = os.path.abspath(settings.LOCAL_STORAGE_DIR)
os.makedirs(artifacts_dir, exist_ok=True)
app.mount("/artifacts", StaticFiles(directory=artifacts_dir), name="artifacts")

@app.get("/")
def root():
    return {
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs_url": "/docs",
        "health_check": "/health/ready",
        "metrics": "/metrics"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("services.api.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
