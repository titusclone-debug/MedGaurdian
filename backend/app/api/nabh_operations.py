"""Readiness and legacy migration operations for the NABH domain."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.auth import assert_hospital_access, get_current_user, require_role
from app.core.database import get_db
from app.models.database import Staff, UserRole
from app.nabh.migration_bridge import migrate_hospital_legacy_nabh_state
from app.nabh.readiness import calculate_hospital_readiness
from app.schemas.nabh import HospitalReadinessResponse, NABHLegacyMigrationReport

router = APIRouter()


@router.get("/readiness/{hospital_id}", response_model=HospitalReadinessResponse)
async def get_hospital_readiness(
    hospital_id: str,
    edition_version: str = Query("6.0"),
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    assert_hospital_access(current_user, hospital_id)
    return calculate_hospital_readiness(db, hospital_id, edition_version)


@router.post("/migration/{hospital_id}/legacy-bridge", response_model=NABHLegacyMigrationReport)
async def run_legacy_migration_bridge(
    hospital_id: str,
    edition_version: str = Query("6.0"),
    dry_run: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: Staff = Depends(require_role([
        UserRole.SUPER_ADMIN,
        UserRole.HOSPITAL_ADMIN,
        UserRole.COMPLIANCE_OFFICER,
    ])),
):
    assert_hospital_access(current_user, hospital_id)
    try:
        report = migrate_hospital_legacy_nabh_state(
            db=db,
            hospital_id=hospital_id,
            edition_version=edition_version,
            dry_run=dry_run,
        )
        if not dry_run:
            db.commit()
        return report
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception:
        db.rollback()
        raise
