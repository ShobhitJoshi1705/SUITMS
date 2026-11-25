from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool, StaticPool
from typing import Generator
import logging
from services.common.config import settings
from services.common.models import Base, HotspotZone
import datetime

logger = logging.getLogger("suitms.database")

# Database URL normalization
db_url = settings.DATABASE_URL
if db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

engine_kwargs = {}

if db_url.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
    engine_kwargs["poolclass"] = StaticPool
else:
    engine_kwargs["poolclass"] = QueuePool
    engine_kwargs["pool_size"] = settings.DB_POOL_SIZE
    engine_kwargs["max_overflow"] = settings.DB_MAX_OVERFLOW
    engine_kwargs["pool_pre_ping"] = settings.DB_POOL_PRE_PING

engine = create_engine(db_url, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator[Session, None, None]:
    """Dependency for providing a transactional database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initializes schema and default metadata/hotspots if absent."""
    logger.info("Initializing database schema...")
    Base.metadata.create_all(bind=engine)
    
    # Seed initial urban zones if none exist
    db = SessionLocal()
    try:
        count = db.query(HotspotZone).count()
        if count == 0:
            logger.info("Seeding initial urban hotspot zones...")
            initial_zones = [
                HotspotZone(
                    zone_id="ZONE-CENTRAL-01",
                    zone_name="MG Road & Central Plaza",
                    latitude=12.9716,
                    longitude=77.5946,
                    radius_meters=450.0,
                    violation_count=18,
                    hazard_count=4,
                    risk_level="HIGH",
                    last_updated=datetime.datetime.utcnow(),
                ),
                HotspotZone(
                    zone_id="ZONE-NORTH-02",
                    zone_name="Outer Ring Road Interchange",
                    latitude=13.0358,
                    longitude=77.5970,
                    radius_meters=600.0,
                    violation_count=29,
                    hazard_count=2,
                    risk_level="SEVERE",
                    last_updated=datetime.datetime.utcnow(),
                ),
                HotspotZone(
                    zone_id="ZONE-EAST-03",
                    zone_name="IT Corridor Express Highway",
                    latitude=12.9352,
                    longitude=77.6245,
                    radius_meters=500.0,
                    violation_count=12,
                    hazard_count=7,
                    risk_level="MEDIUM",
                    last_updated=datetime.datetime.utcnow(),
                ),
                HotspotZone(
                    zone_id="ZONE-SOUTH-04",
                    zone_name="Market Square & Bus Terminal",
                    latitude=12.9250,
                    longitude=77.5838,
                    radius_meters=350.0,
                    violation_count=8,
                    hazard_count=5,
                    risk_level="MEDIUM",
                    last_updated=datetime.datetime.utcnow(),
                ),
            ]
            db.add_all(initial_zones)
            db.commit()
    except Exception as e:
        logger.error(f"Error seeding default hotspot zones: {e}")
        db.rollback()
    finally:
        db.close()
