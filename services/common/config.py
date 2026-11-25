import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "SUITMS - Smart Urban Infrastructure & Traffic Management System"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "production"
    DEBUG: bool = False
    
    # API & Networking
    API_V1_PREFIX: str = "/api/v1"
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    CORS_ORIGINS: str = "*"
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./suitms.db")
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_PRE_PING: bool = True
    
    # Redis
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_PASSWORD: Optional[str] = os.getenv("REDIS_PASSWORD", None)
    REDIS_DB: int = 0
    REDIS_STREAM_VIOLATIONS: str = "traffic:violations:stream"
    REDIS_STREAM_HAZARDS: str = "traffic:hazards:stream"
    REDIS_CONSUMER_GROUP: str = "suitms-workers"
    
    # Object Storage (MinIO / S3)
    S3_ENDPOINT: Optional[str] = os.getenv("S3_ENDPOINT", "http://localhost:9000")
    S3_ACCESS_KEY: str = os.getenv("S3_ACCESS_KEY", "minioadmin")
    S3_SECRET_KEY: str = os.getenv("S3_SECRET_KEY", "minioadmin")
    S3_BUCKET_ARTIFACTS: str = os.getenv("S3_BUCKET_ARTIFACTS", "suitms-artifacts")
    S3_BUCKET_HAZARDS: str = os.getenv("S3_BUCKET_HAZARDS", "suitms-hazards")
    S3_USE_SSL: bool = False
    LOCAL_STORAGE_DIR: str = os.getenv("LOCAL_STORAGE_DIR", "./storage_data")
    
    # Security & Auth
    SECRET_KEY: str = os.getenv("SECRET_KEY", "suitms-super-secret-key-change-in-production-2026")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    
    # Edge Spooler
    SPOOL_DIR: str = os.getenv("SPOOL_DIR", "./edge_spool")
    MAX_SPOOL_SIZE_MB: int = 500
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
