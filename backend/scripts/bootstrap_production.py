"""Create the first hospital and super administrator without demo credentials."""
import argparse
import getpass
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.core.security import hash_password, validate_password_strength
from app.models.database import Hospital, RiskLevel, Staff, UserRole


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap the first MedGuardian production identity.")
    parser.add_argument("--hospital-id", required=True)
    parser.add_argument("--hospital-name", required=True)
    parser.add_argument("--registration-number", required=True)
    parser.add_argument("--state", required=True)
    parser.add_argument("--district", required=True)
    parser.add_argument("--admin-email", required=True)
    parser.add_argument("--admin-name", required=True)
    args = parser.parse_args()

    password = os.environ.get("MEDGUARDIAN_BOOTSTRAP_ADMIN_PASSWORD")
    if not password:
        password = getpass.getpass("Initial super administrator password: ")
    try:
        validate_password_strength(password)
    except ValueError as exc:
        raise SystemExit(str(exc))

    db = SessionLocal()
    try:
        if db.query(Staff).count() or db.query(Hospital).count():
            raise SystemExit("Bootstrap refused: hospital or staff records already exist.")

        hospital = Hospital(
            id=args.hospital_id,
            name=args.hospital_name,
            registration_number=args.registration_number,
            state=args.state,
            district=args.district,
            hospital_type="institution",
            overall_risk_score=0.0,
            risk_level=RiskLevel.LOW,
            onboarding_stage="profile",
        )
        admin = Staff(
            hospital_id=args.hospital_id,
            employee_id="SUPER-001",
            name=args.admin_name,
            role=UserRole.SUPER_ADMIN,
            department="Institutional Governance",
            email=args.admin_email,
            hashed_password=hash_password(password),
            is_active=True,
        )
        db.add_all([hospital, admin])
        db.commit()
        print(f"Production bootstrap complete for hospital_id={args.hospital_id}.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
