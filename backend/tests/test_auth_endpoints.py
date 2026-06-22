from fastapi import status
from app.api.auth import get_current_user
from app.main import app
from app.models.database import Hospital, Staff, UserRole
from app.core.security import hash_password

def test_onboard_hospital_success(client, db_session):
    # Onboard hospital needs SUPER_ADMIN
    async def _super_admin_override():
        return Staff(
            id="super-admin-1",
            hospital_id="system",
            role=UserRole.SUPER_ADMIN,
            name="Super Admin",
            email="superadmin@example.com",
            is_active=True,
        )
    
    app.dependency_overrides[get_current_user] = _super_admin_override

    payload = {
        "name": "Test General Hospital",
        "registration_number": "REG-HOSP-1234",
        "state": "Maharashtra",
        "district": "Mumbai",
        "address": "123 Main St",
        "pincode": "400001",
        "admin_name": "Dr. Admin",
        "admin_email": "admin@testgeneral.com",
        "admin_password": "StrongPassword123"
    }

    response = client.post("/api/auth/onboard-hospital", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    
    data = response.json()
    assert data["status"] == "success"
    assert "hospital_id" in data
    assert data["admin_user"]["email"] == "admin@testgeneral.com"
    assert data["admin_user"]["role"] == "hospital_admin"

    # Verify database entry
    hospital = db_session.query(Hospital).filter(Hospital.registration_number == "REG-HOSP-1234").first()
    assert hospital is not None
    assert hospital.name == "Test General Hospital"

    admin_staff = db_session.query(Staff).filter(Staff.email == "admin@testgeneral.com").first()
    assert admin_staff is not None
    assert admin_staff.role == UserRole.HOSPITAL_ADMIN
    assert admin_staff.name == "Dr. Admin"
    assert admin_staff.hashed_password is not None
    assert admin_staff.hashed_password != "StrongPassword123" # it should be hashed!

    app.dependency_overrides.pop(get_current_user, None)


def test_onboard_hospital_forbidden_for_other_roles(client, db_session):
    # Onboard hospital fails for non-super-admin
    async def _hospital_admin_override():
        return Staff(
            id="hosp-admin-1",
            hospital_id="hosp-1",
            role=UserRole.HOSPITAL_ADMIN,
            name="Hosp Admin",
            email="hospadmin@example.com",
            is_active=True,
        )
    
    app.dependency_overrides[get_current_user] = _hospital_admin_override

    payload = {
        "name": "Test General Hospital 2",
        "registration_number": "REG-HOSP-12345",
        "state": "Maharashtra",
        "district": "Mumbai",
        "address": "123 Main St",
        "pincode": "400001",
        "admin_name": "Dr. Admin 2",
        "admin_email": "admin2@testgeneral.com",
        "admin_password": "StrongPassword123"
    }

    response = client.post("/api/auth/onboard-hospital", json=payload)
    assert response.status_code == status.HTTP_403_FORBIDDEN

    app.dependency_overrides.pop(get_current_user, None)


def test_login_success(client, db_session):
    # First seed a hospital
    hospital = Hospital(
        id="hosp-login-1",
        name="Login Test Hospital",
        registration_number="REG-LOGIN-01",
        hospital_type="trust",
    )
    db_session.add(hospital)
    db_session.commit()

    # Seed user with known password hash
    password = "correct_password"
    hashed = hash_password(password)
    user = Staff(
        id="staff-login-1",
        hospital_id="hosp-login-1",
        employee_id="EMP-LOG-01",
        name="Login User",
        email="login_user@example.com",
        phone="+91-1234567890",
        role=UserRole.DOCTOR,
        department="Emergency",
        hashed_password=hashed,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    # Call login endpoint
    login_data = {
        "username": "login_user@example.com",
        "password": "correct_password"
    }
    response = client.post("/api/auth/login", data=login_data)
    assert response.status_code == status.HTTP_200_OK
    
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "login_user@example.com"
    assert data["user"]["role"] == "doctor"


def test_login_incorrect_password(client, db_session):
    # Seed hospital
    hospital = Hospital(
        id="hosp-login-2",
        name="Login Test Hospital 2",
        registration_number="REG-LOGIN-02",
        hospital_type="trust",
    )
    db_session.add(hospital)
    db_session.commit()

    # Seed user
    password = "correct_password"
    hashed = hash_password(password)
    user = Staff(
        id="staff-login-2",
        hospital_id="hosp-login-2",
        employee_id="EMP-LOG-02",
        name="Login User 2",
        email="login_user2@example.com",
        phone="+91-1234567890",
        role=UserRole.DOCTOR,
        department="Emergency",
        hashed_password=hashed,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    # Call login with WRONG password
    login_data = {
        "username": "login_user2@example.com",
        "password": "wrong_password"
    }
    response = client.post("/api/auth/login", data=login_data)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
