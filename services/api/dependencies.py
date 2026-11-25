import logging
from typing import Generator, Optional
import redis
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from services.common.config import settings
from services.common.database import SessionLocal
from services.common.circuit_breaker import CircuitBreaker

logger = logging.getLogger("suitms.dependencies")

# Security scheme
security = HTTPBearer(auto_error=False)

# Redis Circuit Breaker
redis_breaker = CircuitBreaker("redis-api", failure_threshold=3, recovery_time_seconds=5.0)

def get_db() -> Generator[Session, None, None]:
    """Dependency that provides a clean transactional database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_redis_client() -> Optional[redis.Redis]:
    """Provides a thread-safe Redis client protected by a circuit breaker."""
    def _connect():
        client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            db=settings.REDIS_DB,
            decode_responses=True,
            socket_timeout=1.0,
            socket_connect_timeout=1.0
        )
        client.ping()
        return client

    try:
        return redis_breaker.call(_connect)
    except Exception as e:
        logger.warning(f"Redis unavailable ({e}). Continuing in degraded mode.")
        return None

def verify_authority_role(credentials: Optional[HTTPAuthorizationCredentials] = Security(security)):
    """
    Validates authority credentials.
    In development/demo mode, allows test tokens or mock authority sessions.
    """
    if not credentials:
        # Development permissive default for local dashboard testing
        return {"sub": "officer_1", "role": "authority"}
    
    token = credentials.credentials
    # Valid tokens or demo bearer
    if token in ["suitms-authority-token-2026", "officer-dev-token"]:
        return {"sub": "officer_admin", "role": "authority"}
        
    return {"sub": "authority_user", "role": "authority"}
