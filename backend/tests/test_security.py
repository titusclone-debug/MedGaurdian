import pytest
from fastapi import HTTPException

from app.api.auth import assert_hospital_access
from app.core.security import hash_password, verify_password
from app.models.database import Staff, UserRole


def test_password_hash_is_not_plaintext_and_verifies():
    password = "admin123"

    hashed = hash_password(password)

    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("wrong-password", hashed)


def test_hospital_user_can_access_own_hospital():
    user = Staff(id="user-1", hospital_id="hospital-001", role=UserRole.HOSPITAL_ADMIN)

    assert_hospital_access(user, "hospital-001")


def test_hospital_user_cannot_access_other_hospital():
    user = Staff(id="user-1", hospital_id="hospital-001", role=UserRole.HOSPITAL_ADMIN)

    with pytest.raises(HTTPException) as exc:
        assert_hospital_access(user, "hospital-002")

    assert exc.value.status_code == 403


def test_super_admin_can_access_any_hospital():
    user = Staff(id="user-1", hospital_id="hospital-001", role=UserRole.SUPER_ADMIN)

    assert_hospital_access(user, "hospital-002")


@pytest.mark.anyio
async def test_require_role_allows_authorized_role():
    from app.api.auth import require_role
    
    checker = require_role([UserRole.SUPER_ADMIN, UserRole.HOSPITAL_ADMIN])
    user = Staff(id="user-1", role=UserRole.HOSPITAL_ADMIN)
    
    res = await checker(current_user=user)
    assert res == user


@pytest.mark.anyio
async def test_require_role_denies_unauthorized_role():
    from app.api.auth import require_role
    
    checker = require_role([UserRole.SUPER_ADMIN, UserRole.HOSPITAL_ADMIN])
    user = Staff(id="user-1", role=UserRole.DOCTOR)
    
    with pytest.raises(HTTPException) as exc:
        await checker(current_user=user)
        
    assert exc.value.status_code == 403
