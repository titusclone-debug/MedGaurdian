from datetime import datetime, timedelta
from fastapi import status

from app.api.auth import get_current_user
from app.main import app
from app.models.database import (
    Hospital,
    Staff,
    UserRole,
    License,
    LicenseStatus,
    BMWLog,
    BMWCategory,
    FundAccount,
    FundType,
)

TEST_HOSPITAL_ID = "reports-hospital-1"


def _seed_report_data(db_session):
    hospital = Hospital(
        id=TEST_HOSPITAL_ID,
        name="Reports Test Hospital",
        registration_number="REP-REG-001",
        hospital_type="trust",
        bed_count=100,
        state="Karnataka",
        district="Bengaluru",
        fcra_number="FCRA-REP-999",
        nabh_accreditation_id="NABH-REP-123",
    )
    db_session.add(hospital)

    # 2 Licenses (active)
    lic1 = License(
        hospital_id=TEST_HOSPITAL_ID,
        license_name="Medical License 1",
        license_number="LIC-REP-01",
        issuing_authority="State Board",
        status=LicenseStatus.ACTIVE,
        expiry_date=datetime.utcnow() + timedelta(days=120),
    )
    lic2 = License(
        hospital_id=TEST_HOSPITAL_ID,
        license_name="Medical License 2",
        license_number="LIC-REP-02",
        issuing_authority="State Board",
        status=LicenseStatus.ACTIVE,
        expiry_date=datetime.utcnow() + timedelta(days=60),
    )
    db_session.add(lic1)
    db_session.add(lic2)

    # 1 BMWLog
    bmw = BMWLog(
        hospital_id=TEST_HOSPITAL_ID,
        waste_date=datetime.utcnow(),
        category=BMWCategory.YELLOW,
        weight_kg=12.5,
        source_department="ICU",
        source_ward="A",
    )
    db_session.add(bmw)

    # 1 FCRA Account
    fcra = FundAccount(
        id="fcra-rep-acc-1",
        hospital_id=TEST_HOSPITAL_ID,
        account_name="Reports FCRA Account",
        account_number="999988887777",
        bank_name="Reports Bank",
        branch="Reports Branch",
        fund_type=FundType.FCRA_FOREIGN,
        is_fcra_designated=True,
    )
    db_session.add(fcra)

    db_session.commit()


def _override_user():
    async def _user_override():
        return Staff(
            id="user-rep-admin",
            hospital_id=TEST_HOSPITAL_ID,
            role=UserRole.HOSPITAL_ADMIN,
            name="Report Admin",
            email="repadmin@example.com",
            is_active=True,
        )

    return _user_override


def test_compliance_summary_json(client, db_session):
    _seed_report_data(db_session)
    app.dependency_overrides[get_current_user] = _override_user()

    response = client.get(f"/api/reports/compliance-summary/{TEST_HOSPITAL_ID}?format=json")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["report_type"] == "Comprehensive Compliance Summary"
    assert data["hospital"]["name"] == "Reports Test Hospital"
    assert data["sections"]["licenses"]["total"] == 2
    assert data["sections"]["licenses"]["active"] == 2
    assert data["sections"]["bmw"]["total_entries"] == 1
    assert data["sections"]["fcra"]["designated_accounts"] == 1

    app.dependency_overrides.pop(get_current_user, None)


def test_compliance_summary_csv(client, db_session):
    _seed_report_data(db_session)
    app.dependency_overrides[get_current_user] = _override_user()

    response = client.get(f"/api/reports/compliance-summary/{TEST_HOSPITAL_ID}?format=csv")
    assert response.status_code == status.HTTP_200_OK
    assert "Content-Disposition" in response.headers
    assert f"compliance_report_{TEST_HOSPITAL_ID}.csv" in response.headers["Content-Disposition"]

    csv_text = response.text
    assert "Section,Metric,Value" in csv_text
    assert "licenses,total,2" in csv_text
    assert "bmw,total_entries,1" in csv_text
    assert "fcra,designated_accounts,1" in csv_text

    app.dependency_overrides.pop(get_current_user, None)
