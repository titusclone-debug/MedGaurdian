from app.api.auth import login_limiter
from app.main import app
from app.models.database import AuditLog, Hospital, Staff, UserRole
from app.core.security import hash_password


EXPECTED_NABH_PATHS = {
    "/api/nabh/ontology/coverage",
    "/api/nabh/ontology/editions",
    "/api/nabh/ontology/chapters",
    "/api/nabh/ontology/requirements",
    "/api/nabh/ontology/requirements/{requirement_id}",
    "/api/nabh/ontology/requirements/{requirement_id}/explanation",
    "/api/nabh/profile/{hospital_id}",
    "/api/nabh/profile/{hospital_id}/compute-applicability",
    "/api/nabh/requirements/{hospital_id}",
    "/api/nabh/requirements/{hospital_id}/evidence-plan",
    "/api/nabh/requirements/{hospital_id}/{requirement_id}",
    "/api/nabh/readiness/{hospital_id}",
    "/api/nabh/migration/{hospital_id}/legacy-bridge",
}


def test_phase_one_nabh_public_paths_remain_registered():
    paths = set(app.openapi()["paths"])
    assert EXPECTED_NABH_PATHS <= paths


def test_failed_login_attempts_are_rate_limited(client):
    login_limiter.clear("testclient:missing@example.com")
    for _ in range(5):
        response = client.post(
            "/api/auth/login",
            data={"username": "missing@example.com", "password": "wrong"},
        )
        assert response.status_code == 401

    response = client.post(
        "/api/auth/login",
        data={"username": "missing@example.com", "password": "wrong"},
    )
    assert response.status_code == 429
    assert "Retry-After" in response.headers
    login_limiter.clear("testclient:missing@example.com")


def test_password_reset_requires_reauthentication_and_is_audited(client, db_session):
    hospital = Hospital(id="hospital-reset", name="Reset Hospital")
    admin = Staff(
        id="admin-reset",
        hospital_id=hospital.id,
        employee_id="ADMIN-RESET",
        name="Reset Admin",
        email="admin-reset@example.com",
        role=UserRole.HOSPITAL_ADMIN,
        hashed_password=hash_password("admin-current-password"),
        is_active=True,
    )
    target = Staff(
        id="target-reset",
        hospital_id=hospital.id,
        employee_id="TARGET-RESET",
        name="Target User",
        email="target-reset@example.com",
        role=UserRole.DOCTOR,
        hashed_password=hash_password("old-password"),
        is_active=True,
    )
    db_session.add_all([hospital, admin, target])
    db_session.commit()

    login = client.post(
        "/api/auth/login",
        data={"username": admin.email, "password": "admin-current-password"},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    rejected = client.post(
        "/api/auth/reset-staff-password",
        headers=headers,
        json={
            "target_email": target.email,
            "new_password": "NewStrongPassword123",
            "current_password": "wrong-password",
        },
    )
    assert rejected.status_code == 403

    accepted = client.post(
        "/api/auth/reset-staff-password",
        headers=headers,
        json={
            "target_email": target.email,
            "new_password": "NewStrongPassword123",
            "current_password": "admin-current-password",
        },
    )
    assert accepted.status_code == 200
    audit = db_session.query(AuditLog).filter(
        AuditLog.action == "staff_password_reset",
        AuditLog.resource_id == target.id,
    ).one()
    assert audit.user_id == admin.id
