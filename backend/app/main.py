"""
MedGuardian - Main Application
The Institutional Nervous System
"""
from contextlib import asynccontextmanager
from datetime import datetime
import logging
import os

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    admin,
    auth,
    bmw,
    dashboard,
    dpdp,
    fcra,
    licenses,
    nabh,
    regulatory,
    reports,
    risk,
)
from app.api.auth import get_current_user
from app.core.config import settings
from app.core.database import engine, get_db
from app.models.database import Base, Staff

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _is_deployed_environment() -> tuple[bool, bool]:
    """Return Render/production flags used for startup safety gates."""
    return os.environ.get("RENDER") == "true", os.environ.get("APP_ENV") == "production"


def _assert_durable_database_for_deployment() -> tuple[bool, bool]:
    """
    Prevent deployed environments from silently falling back to ephemeral SQLite.
    This must run before any schema creation or seeding touches the database.
    """
    is_render, is_production = _is_deployed_environment()
    detected_dialect = engine.dialect.name
    db_url = settings.DATABASE_URL

    if (is_render or is_production) and detected_dialect == "sqlite":
        is_default = db_url == "sqlite:///./medguardian.db"
        err_msg = (
            "PRODUCTION SECURITY VIOLATION: MedGuardian is starting on Render/production, "
            f"but detected database dialect is '{detected_dialect}' (ephemeral local storage). "
            f"DATABASE_URL missing/defaulted: {is_default}. "
            "REQUIRED ACTION: Configure a Managed PostgreSQL database in Render/production dashboard settings."
        )
        logger.critical(err_msg)
        raise RuntimeError(err_msg)

    return is_render, is_production


def _seed_demo_data_if_allowed(staff_count: int, is_render: bool, is_production: bool) -> None:
    """Bootstrap demo data only when local/dev or an explicit production bootstrap flag permits it."""
    if staff_count > 0:
        return

    if is_render or is_production:
        if os.environ.get("AUTO_SEED_DEMO_ON_STARTUP") != "true":
            err_msg = (
                "PRODUCTION STARTUP ABORTED: no staff records exist. "
                "MedGuardian will not silently create demo users in a deployed environment. "
                "REQUIRED ACTION: run an approved bootstrap/identity seeding step, or set "
                "AUTO_SEED_DEMO_ON_STARTUP=true only for a controlled initial bootstrap."
            )
            logger.critical(err_msg)
            raise RuntimeError(err_msg)

        logger.warning(
            "Production bootstrap is explicitly configured to run demo mock seeding "
            "because AUTO_SEED_DEMO_ON_STARTUP=true."
        )
    else:
        logger.info("Database empty. Triggering automated demo mock seeding...")

    from scripts.seed_data import seed

    seed()


def _validate_nabh_seed_health(db, is_render: bool, is_production: bool) -> None:
    """Validate the NABH truth layer and optionally run the explicit startup seeder."""
    from app.nabh.seed_health import check_nabh_seed_health

    seed_health = check_nabh_seed_health(db)
    if seed_health["is_healthy"]:
        logger.info(f"NABH 6.0 ontology seed health verified: {seed_health}")
        return

    if os.environ.get("AUTO_SEED_NABH_ON_STARTUP") == "true":
        logger.info("NABH 6.0 ontology is unseeded or incomplete. Triggering auto-seeding...")
        from app.nabh.seeder import seed_versioned_ontology

        seed_versioned_ontology(db, "app/nabh/data", "6.0")
        seed_health = check_nabh_seed_health(db)
        if seed_health["is_healthy"]:
            logger.info(f"NABH 6.0 ontology seed health verified after auto-seed: {seed_health}")
            return

        err_msg = (
            "PRODUCTION STARTUP ABORTED: NABH 6.0 ontology remained unhealthy after auto-seeding. "
            f"Details: {seed_health}."
        )
        logger.critical(err_msg)
        raise RuntimeError(err_msg)

    if is_render or is_production:
        err_msg = (
            "PRODUCTION STARTUP ABORTED: NABH 6.0 ontology is unseeded or corrupted. "
            f"Details: {seed_health}. "
            "REQUIRED ACTION: Run the dedicated CLI seeding script: "
            "'python backend/scripts/seed_nabh_ontology.py --edition 6.0' or configure "
            "AUTO_SEED_NABH_ON_STARTUP=true for a controlled initial bootstrap."
        )
        logger.critical(err_msg)
        raise RuntimeError(err_msg)

    logger.warning(
        "DATABASE LIFECYCLE WARNING: NABH 6.0 ontology is unseeded or corrupted. "
        f"Details: {seed_health}."
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("MedGuardian - The Institutional Nervous System - Starting...")
    logger.info(f"Hospital: {settings.HOSPITAL_NAME}")
    logger.info("NABH Edition: 6th")
    logger.info("DPDP Compliance: Active")
    logger.info("FCRA Guardian: Active")

    is_render, is_production = _assert_durable_database_for_deployment()

    # Ensure database schema is created on startup.
    Base.metadata.create_all(bind=engine)

    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        staff_count = db.query(Staff).count()
        _seed_demo_data_if_allowed(staff_count, is_render, is_production)
        _validate_nabh_seed_health(db, is_render, is_production)
    except Exception as e:
        logger.error(f"Failed during database startup validation: {e}")
        if is_render or is_production:
            raise
    finally:
        db.close()

    # Initialize ChromaDB collections.
    from app.services.vector_store import init_chromadb

    init_chromadb()

    # Start regulatory monitoring scheduler.
    from app.services.scheduler import start_scheduler

    start_scheduler()

    yield

    logger.info("MedGuardian shutting down gracefully...")


app = FastAPI(
    title="MedGuardian API",
    description="""
    ## The Institutional Nervous System for Hospital Administration

    MedGuardian automates compliance, asset protection, and operational excellence
    for healthcare institutions. Built for the 2026 regulatory era.

    ### Key Modules:
    - **FCRA Guardian** - Foreign fund compliance and utilization tracking
    - **DPDP Consent Manager** - Patient data protection and consent management
    - **BMW Sentinel** - Bio-medical waste tracking and audit readiness
    - **NABH Compliance Tracker** - 6th Edition accreditation management
    - **Risk Weather Forecast** - Predictive institutional risk intelligence
    - **Bureaucracy Engine** - Auto-drafted legal documents and renewals
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
        },
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """System health check with component status."""
    from sqlalchemy import text

    health = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {},
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
