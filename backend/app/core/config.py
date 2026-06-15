"""
MedGuardian — Core Configuration
The Institutional Nervous System for Hospital Administration
"""
from pydantic import ConfigDict
from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings with sensible defaults for mission hospitals."""
    model_config = ConfigDict(env_file=".env", case_sensitive=True)
    
    # Application
    APP_NAME: str = "MedGuardian"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production"
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]
    
    # Database
    DATABASE_URL: str = "sqlite:///./medguardian.db"
    
    # ChromaDB (Local-First Vector Store)
    CHROMA_PERSIST_DIR: str = "./data/chromadb"
    CHROMA_COLLECTION_REGULATIONS: str = "regulations"
    CHROMA_COLLECTION_POLICIES: str = "policies"
    CHROMA_COLLECTION_CONSENT: str = "consent_artefacts"
    
    # JWT Auth
    JWT_SECRET_KEY: str = "change-me-jwt-secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 hour shifts
    
    # Hospital Identity
    HOSPITAL_NAME: str = "Mission Hospital"
    HOSPITAL_FCRA_NUMBER: Optional[str] = None
    HOSPITAL_NABH_ID: Optional[str] = None
    HOSPITAL_STATE: str = "Kerala"
    HOSPITAL_DISTRICT: str = ""
    
    # Regulatory Sources
    GAZETTE_RSS_URL: str = "https://egazette.gov.in/rss"
    MOHFW_NOTIFICATIONS_URL: str = "https://mohfw.gov.in"
    NABH_PORTAL_URL: str = "https://portal.nabh.co"
    
    # AI/ML
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 50
    
    # BMW Tracking
    BMW_CATEGORIES: list = [
        "Yellow",  # Human anatomical, soiled, expired medicines
        "Red",     # Contaminated waste (recyclable)
        "White",   # Sharps waste
        "Blue",    # Medicines, cytotoxic waste
        "Black",   # General municipal solid waste
    ]
    
    # DPDP Compliance
    CONSENT_RETENTION_DAYS: int = 365 * 3  # 3 years default
    DATA_BREACH_NOTIFICATION_HOURS: int = 72
    
    # Risk Scoring Weights
    RISK_WEIGHTS: dict = {
        "fcra_compliance": 0.25,
        "nabh_readiness": 0.20,
        "dpdp_consent": 0.15,
        "bmw_compliance": 0.15,
        "license_expiry": 0.10,
        "staffing_adequacy": 0.10,
        "equipment_maintenance": 0.05,
    }
    
settings = Settings()

# Normalize postgres:// to postgresql:// for SQLAlchemy 2.0 compatibility
if settings.DATABASE_URL.startswith("postgres://"):
    settings.DATABASE_URL = settings.DATABASE_URL.replace("postgres://", "postgresql://", 1)

