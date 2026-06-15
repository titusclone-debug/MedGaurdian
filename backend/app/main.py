"""
MedGuardian — Main Application
The Institutional Nervous System
"""
from fastapi import FastAPI, HTTPException, Depends, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Optional, List
import logging

from app.core.config import settings
from app.models.database import (
    Base, Hospital, Staff, FundAccount, FundTransaction,
    ConsentRecord, BMWLog, License, ComplianceRecord,
    RiskAlert, RegulatoryUpdate, AuditLog
)
from app.core.database import engine, get_db
from app.api import (
    dashboard, fcra, dpdp, bmw, nabh, licenses,
    risk, regulatory, auth, reports, admin
)
from app.api.auth import get_current_user

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("🏥 MedGuardian — The Institutional Nervous System — Starting...")
    logger.info(f"📊 Hospital: {settings.HOSPITAL_NAME}")
    logger.info(f"📋 NABH Edition: 6th")
    logger.info(f"🔒 DPDP Compliance: Active")
    logger.info(f"💰 FCRA Guardian: Active")
    
    # Ensure database schema is created on startup
    Base.metadata.create_all(bind=engine)
    
    # 1. ENFORCE PRODUCTION DATABASE PERSISTENCE
    import os
    is_render = os.environ.get("RENDER") == "true"
    is_production = os.environ.get("APP_ENV") == "production"
    db_url = settings.DATABASE_URL
    
    if (is_render or is_production) and "sqlite" in db_url.lower():
        detected_dialect = "sqlite"
        is_default = db_url == "sqlite:///./medguardian.db"
        err_msg = (
            f"❌ PRODUCTION SECURITY VIOLATION: MedGuardian is starting on Render/production, "
            f"but detected database dialect is '{detected_dialect}' (ephemeral local storage). "
            f"DATABASE_URL missing/defaulted: {is_default}. "
            f"REQUIRED ACTION: Configure a Managed PostgreSQL database in Render/production dashboard settings."
        )
        logger.critical(err_msg)
        raise RuntimeError(err_msg)

    # 2. VALIDATE ONTOLOGY SEED INTEGRITY
    from app.core.database import SessionLocal
    from app.nabh.seed_health import check_nabh_seed_health
    from app.models.database import Staff
    
    db = SessionLocal()
    try:
        # Check standard demo seeding (Mock data)
        staff_count = db.query(Staff).count()
        if staff_count == 0:
            logger.info("🗄️ Database empty. Triggering automated demo mock seeding...")
            from scripts.seed_data import seed
            seed()
            
        # Verify NABH ontology seed health
        seed_health = check_nabh_seed_health(db)
        if not seed_health["is_healthy"]:
            # Auto-seed if explicitly configured via environment
            if os.environ.get("AUTO_SEED_NABH_ON_STARTUP") == "true":
                logger.info("🌱 NABH 6.0 ontology is unseeded or incomplete. Triggering auto-seeding...")
                from app.nabh.seeder import seed_versioned_ontology
                seed_versioned_ontology(db, "app/nabh/data", "6.0")
            elif is_render or is_production:
                # Abort startup in production if ontology is missing
                err_msg = (
                    f"❌ PRODUCTION STARTUP ABORTED: NABH 6.0 ontology is unseeded or corrupted. "
                    f"Details: {seed_health}. "
                    f"REQUIRED ACTION: Run the dedicated CLI seeding script: "
                    f"'python backend/scripts/seed_nabh_ontology.py --edition 6.0' or configure AUTO_SEED_NABH_ON_STARTUP=true."
                )
                logger.critical(err_msg)
                raise RuntimeError(err_msg)
            else:
                logger.warning(
                    f"⚠️ DATABASE LIFECYCLE WARNING: NABH 6.0 ontology is unseeded or corrupted. "
                    f"Details: {seed_health}."
                )
    except Exception as e:
        logger.error(f"Failed during database startup validation: {e}")
        if is_render or is_production:
            raise e
    finally:
        db.close()
    
    # Initialize ChromaDB collections
    from app.services.vector_store import init_chromadb
    init_chromadb()
    
    # Start regulatory monitoring scheduler
    from app.services.scheduler import start_scheduler
    start_scheduler()
    
    yield
    
    logger.info("🏥 MedGuardian shutting down gracefully...")


app = FastAPI(
    title="MedGuardian API",
    description="""
    ## The Institutional Nervous System for Hospital Administration
    
    MedGuardian automates compliance, asset protection, and operational excellence 
    for healthcare institutions. Built for the 2026 regulatory era.
    
    ### Key Modules:
    - **FCRA Guardian** — Foreign fund compliance and utilization tracking
    - **DPDP Consent Manager** — Patient data protection and consent management
    - **BMW Sentinel** — Bio-medical waste tracking and audit readiness
    - **NABH Compliance Tracker** — 6th Edition accreditation management
    - **Risk Weather Forecast** — Predictive institutional risk intelligence
    - **Bureaucracy Engine** — Auto-drafted legal documents and renewals
    """,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
protected_dependencies = [Depends(get_current_user)]
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"], dependencies=protected_dependencies)
app.include_router(fcra.router, prefix="/api/fcra", tags=["FCRA Guardian"], dependencies=protected_dependencies)
app.include_router(dpdp.router, prefix="/api/dpdp", tags=["DPDP Consent Manager"], dependencies=protected_dependencies)
app.include_router(bmw.router, prefix="/api/bmw", tags=["BMW Sentinel"], dependencies=protected_dependencies)
app.include_router(nabh.router, prefix="/api/nabh", tags=["NABH Compliance"], dependencies=protected_dependencies)
app.include_router(licenses.router, prefix="/api/licenses", tags=["License Tracker"], dependencies=protected_dependencies)
app.include_router(risk.router, prefix="/api/risk", tags=["Risk Intelligence"], dependencies=protected_dependencies)
app.include_router(regulatory.router, prefix="/api/regulatory", tags=["Regulatory Monitor"], dependencies=protected_dependencies)
app.include_router(reports.router, prefix="/api/reports", tags=["Reports & Export"], dependencies=protected_dependencies)
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"], dependencies=protected_dependencies)


@app.get("/", tags=["Root"])
async def root():
    return {
        "name": "MedGuardian",
        "version": settings.APP_VERSION,
        "tagline": "The Institutional Nervous System",
        "status": "operational",
        "modules": {
            "fcra_guardian": "active",
            "dpdp_consent": "active",
            "bmw_sentinel": "active",
            "nabh_tracker": "active",
            "risk_forecast": "active",
            "bureaucracy_engine": "active",
        }
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """System health check with component status."""
    from sqlalchemy import text
    
    health = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {}
    }
    
    # Database check
    try:
        db = next(get_db())
        db.execute(text("SELECT 1"))
        health["components"]["database"] = "healthy"
    except Exception as e:
        health["components"]["database"] = f"unhealthy: {str(e)}"
        health["status"] = "degraded"
    
    # ChromaDB check
    try:
        from app.services.vector_store import get_chroma_client
        get_chroma_client()
        health["components"]["vector_store"] = "healthy"
    except Exception as e:
        health["components"]["vector_store"] = f"unhealthy: {str(e)}"
        health["status"] = "degraded"
    
    return health
