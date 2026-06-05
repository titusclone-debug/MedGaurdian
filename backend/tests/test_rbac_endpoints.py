from fastapi import status

from app.api.auth import get_current_user
from app.main import app
from app.models.database import FundAccount, FundType, Hospital, Staff, UserRole


TEST_HOSPITAL_ID = "rbac-hospital-1"
TEST_PATH = f"/api/fcra/accounts/{TEST_HOSPITAL_ID}"


def _seed_hospital_and_account(db_session):
    hospital = Hospital(
        id=TEST_HOSPITAL_ID,
        name="RBAC Test Hospital",
        registration_number="RBAC-REG-001",
        hospital_type="trust",
    )
    account = FundAccount(
        id="rbac-fcra-account-1",
        hospital_id=TEST_HOSPITAL_ID,
        account_name="RBAC FCRA Account",
        account_number="111122223333",
        bank_name="RBAC Bank",
        branch="Main",
        fund_type=FundType.FCRA_FOREIGN,
        is_fcra_designated=True,
        fcra_utilization_purpose="patient care",
    )
    db_session.add(hospital)
    db_session.add(account)
    db_session.commit()


def _override_user(role: UserRole, hospital_id: str = TEST_HOSPITAL_ID):
    async def _user_override():
        return Staff(
            id=f"user-{role.value}",
            hospital_id=hospital_id,
            role=role,
            name=f"{role.value} user",
            email=f"{role.value}@example.com",
            is_active=True,
        )

    return _user_override


def test_fcra_accounts_rbac_access_matrix(client, db_session):
    _seed_hospital_and_account(db_session)

    app.dependency_overrides[get_current_user] = _override_user(UserRole.SUPER_ADMIN)
    super_admin_response = client.get(TEST_PATH)
    assert super_admin_response.status_code == status.HTTP_200_OK

    app.dependency_overrides[get_current_user] = _override_user(UserRole.HOSPITAL_ADMIN)
    hospital_admin_response = client.get(TEST_PATH)
    assert hospital_admin_response.status_code == status.HTTP_200_OK

    app.dependency_overrides[get_current_user] = _override_user(UserRole.DOCTOR)
    doctor_response = client.get(TEST_PATH)
    assert doctor_response.status_code == status.HTTP_403_FORBIDDEN

    app.dependency_overrides.pop(get_current_user, None)
    unauthenticated_response = client.get(TEST_PATH)
    assert unauthenticated_response.status_code == status.HTTP_401_UNAUTHORIZED
