"""Authentication and Authorization — JWT + RBAC."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.database import Staff, UserRole, Hospital, RiskLevel

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


class UserCreate(BaseModel):
    hospital_id: str
    name: str
    email: str
    phone: str
    role: str
    department: str
    employee_id: str
    qualification: Optional[str] = None
    registration_number: Optional[str] = None
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict


class HospitalOnboard(BaseModel):
    name: str
    registration_number: str
    state: str
    district: str
    address: str
    pincode: str
    admin_name: str
    admin_email: str
    admin_password: str


class ResetPasswordSchema(BaseModel):
    target_email: str
    new_password: str


class HospitalOnboardUpdate(BaseModel):
    onboarding_stage: str
    bed_count: Optional[int] = None
    hospital_type: Optional[str] = None
    has_emergency: Optional[bool] = None
    has_icu: Optional[bool] = None
    has_operation_theatre: Optional[bool] = None
    fcra_number: Optional[str] = None


class StaffCreateSchema(BaseModel):
    name: str
    email: str
    phone: str
    role: str
    department: str
    employee_id: str
    qualification: Optional[str] = None
    password: str


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Staff:
    """Dependency to get current authenticated user."""
    from jose import jwt, JWTError
    from app.core.config import settings

    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(Staff).filter(Staff.id == user_id).first()
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid token")

    return user


def require_role(allowed_roles: list[UserRole]):
    """Dependency factory to enforce role-based access."""
    async def role_checker(current_user: Staff = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role {current_user.role.value} not authorized for this action"
            )
        return current_user
    return role_checker


def assert_hospital_access(current_user: Staff, hospital_id: str) -> None:
    """Ensure the authenticated user can access the requested hospital."""
    if current_user.role == UserRole.SUPER_ADMIN:
        return
    if current_user.hospital_id != hospital_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized for this hospital"
        )


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Authenticate user and return JWT token."""
    # Find user by email
    user = db.query(Staff).filter(Staff.email == form_data.username).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.hashed_password or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )
    
    access_token = create_access_token(user.id, {
        "email": user.email,
        "role": user.role.value,
        "hospital_id": user.hospital_id,
        "name": user.name,
    })
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role.value,
            "department": user.department,
            "hospital_id": user.hospital_id,
        }
    }


@router.post("/register")
async def register_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(require_role([UserRole.SUPER_ADMIN, UserRole.HOSPITAL_ADMIN])),
):
    """Register a new staff member."""
    assert_hospital_access(current_user, user_data.hospital_id)

    # Check for existing email
    existing = db.query(Staff).filter(Staff.email == user_data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    new_user = Staff(
        hospital_id=user_data.hospital_id,
        name=user_data.name,
        email=user_data.email,
        phone=user_data.phone,
        role=UserRole(user_data.role),
        department=user_data.department,
        employee_id=user_data.employee_id,
        qualification=user_data.qualification,
        registration_number=user_data.registration_number,
        hashed_password=hash_password(user_data.password),
        is_active=True,
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {
        "id": new_user.id,
        "message": "User registered successfully",
        "role": new_user.role.value
    }


@router.post("/onboard-hospital", status_code=status.HTTP_201_CREATED)
async def onboard_hospital(
    onboard_data: HospitalOnboard,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(require_role([UserRole.SUPER_ADMIN])),
):
    """
    Onboard a brand new hospital tenant network along with their head administrator.
    Only accessible by SUPER_ADMIN.
    """
    import re
    import uuid

    # Check if registration number already exists
    existing_hospital = db.query(Hospital).filter(Hospital.registration_number == onboard_data.registration_number).first()
    if existing_hospital:
        raise HTTPException(
            status_code=400,
            detail="Hospital registration number already onboarded."
        )

    # Check if admin email already exists
    existing_email = db.query(Staff).filter(Staff.email == onboard_data.admin_email).first()
    if existing_email:
        raise HTTPException(
            status_code=400,
            detail="Admin email already registered."
        )

    # Generate a clean, structured hospital ID
    slug = re.sub(r'[^a-z0-9]', '', onboard_data.name.lower())[:15]
    hospital_id = f"hospital-{slug}-{uuid.uuid4().hex[:6]}"

    # 1. Create the new Hospital tenant
    new_hospital = Hospital(
        id=hospital_id,
        name=onboard_data.name,
        registration_number=onboard_data.registration_number,
        state=onboard_data.state,
        district=onboard_data.district,
        address=onboard_data.address,
        pincode=onboard_data.pincode,
        hospital_type="trust",
        overall_risk_score=0.0,
        risk_level=RiskLevel.LOW,
    )
    db.add(new_hospital)

    # 2. Create their head administrator staff account
    new_admin = Staff(
        id=f"staff-{uuid.uuid4().hex[:6]}",
        hospital_id=hospital_id,
        employee_id=f"ADM-{uuid.uuid4().hex[:4].upper()}",
        name=onboard_data.admin_name,
        email=onboard_data.admin_email,
        phone="+91-9999999999",
        role=UserRole.HOSPITAL_ADMIN,
        department="Administration",
        qualification="MD (Hospital Administration)",
        hashed_password=hash_password(onboard_data.admin_password),
        is_active=True,
    )
    db.add(new_admin)
    
    db.commit()
    db.refresh(new_hospital)
    db.refresh(new_admin)

    return {
        "status": "success",
        "message": f"Hospital '{new_hospital.name}' onboarded successfully.",
        "hospital_id": new_hospital.id,
        "admin_user": {
            "id": new_admin.id,
            "name": new_admin.name,
            "email": new_admin.email,
            "role": new_admin.role.value
        }
    }


@router.get("/hospitals")
async def get_hospitals(
    db: Session = Depends(get_db),
    current_user: Staff = Depends(require_role([UserRole.SUPER_ADMIN])),
):
    """Fetch all onboarded hospitals. Super Admin only."""
    hospitals = db.query(Hospital).all()
    result = []
    for h in hospitals:
        # Find primary administrator
        admin = db.query(Staff).filter(
            Staff.hospital_id == h.id, 
            Staff.role == UserRole.HOSPITAL_ADMIN
        ).first()
        
        result.append({
            "id": h.id,
            "name": h.name,
            "registration_number": h.registration_number,
            "state": h.state,
            "district": h.district,
            "onboarding_stage": h.onboarding_stage,
            "created_at": h.created_at,
            "admin_email": admin.email if admin else "N/A",
            "admin_name": admin.name if admin else "N/A"
        })
    return result


@router.post("/reset-staff-password")
async def reset_staff_password(
    data: ResetPasswordSchema,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    """
    Secure password reset endpoint.
    - Super Admin can reset ANY account's password.
    - Hospital Admin can reset staff passwords within their own hospital.
    """
    target = db.query(Staff).filter(Staff.email == data.target_email).first()
    if not target:
        raise HTTPException(status_code=404, detail="Target user not found.")
        
    # Security gates
    if current_user.role == UserRole.SUPER_ADMIN:
        # Super Admin has global override authority
        pass
    elif current_user.role == UserRole.HOSPITAL_ADMIN:
        # Hospital Admin can only override within their tenant, and cannot reset other admins or super admins
        if target.hospital_id != current_user.hospital_id:
            raise HTTPException(status_code=403, detail="Access denied: Different tenant.")
        if target.role in [UserRole.SUPER_ADMIN, UserRole.HOSPITAL_ADMIN]:
            raise HTTPException(status_code=403, detail="Access denied: Cannot reset administrative roles.")
    else:
        raise HTTPException(status_code=403, detail="Access denied.")
        
    target.hashed_password = hash_password(data.new_password)
    db.commit()
    return {"status": "success", "message": f"Password for {data.target_email} updated successfully."}


@router.put("/hospitals/onboard")
async def update_onboarding_wizard(
    data: HospitalOnboardUpdate,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(require_role([UserRole.HOSPITAL_ADMIN])),
):
    """Update onboarding stage and metadata settings for the admin's hospital."""
    hospital = db.query(Hospital).filter(Hospital.id == current_user.hospital_id).first()
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital tenant not found.")
        
    hospital.onboarding_stage = data.onboarding_stage
    
    if data.bed_count is not None:
        hospital.bed_count = data.bed_count
    if data.hospital_type is not None:
        hospital.hospital_type = data.hospital_type
    if data.has_emergency is not None:
        hospital.has_emergency = data.has_emergency
    if data.has_icu is not None:
        hospital.has_icu = data.has_icu
    if data.has_operation_theatre is not None:
        hospital.has_operation_theatre = data.has_operation_theatre
    if data.fcra_number is not None:
        hospital.fcra_number = data.fcra_number
        
    db.commit()
    db.refresh(hospital)
    return {
        "status": "success",
        "onboarding_stage": hospital.onboarding_stage,
        "bed_count": hospital.bed_count,
        "fcra_number": hospital.fcra_number
    }


@router.get("/staff")
async def list_hospital_staff(
    db: Session = Depends(get_db),
    current_user: Staff = Depends(require_role([UserRole.HOSPITAL_ADMIN, UserRole.SUPER_ADMIN])),
):
    """Get all staff members registered in the current administrator's hospital."""
    # Scope check
    staff_members = db.query(Staff).filter(
        Staff.hospital_id == current_user.hospital_id,
        Staff.role != UserRole.SUPER_ADMIN
    ).all()
    return [{
        "id": s.id,
        "name": s.name,
        "email": s.email,
        "phone": s.phone,
        "role": s.role.value,
        "department": s.department,
        "employee_id": s.employee_id,
        "qualification": s.qualification,
        "is_active": s.is_active
    } for s in staff_members]


@router.post("/staff", status_code=status.HTTP_201_CREATED)
async def create_hospital_staff(
    data: StaffCreateSchema,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(require_role([UserRole.HOSPITAL_ADMIN])),
):
    """Create a new staff member (doctor, nurse, etc.) scoped to the admin's hospital."""
    # Check if email is already taken
    existing_email = db.query(Staff).filter(Staff.email == data.email).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already registered.")
        
    # Check role eligibility
    try:
        assigned_role = UserRole(data.role)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid staff role specified.")
        
    if assigned_role in [UserRole.SUPER_ADMIN, UserRole.HOSPITAL_ADMIN]:
        raise HTTPException(status_code=403, detail="Cannot assign administrative roles.")
        
    import uuid
    new_staff = Staff(
        id=f"staff-{uuid.uuid4().hex[:6]}",
        hospital_id=current_user.hospital_id,
        employee_id=data.employee_id,
        name=data.name,
        email=data.email,
        phone=data.phone,
        role=assigned_role,
        department=data.department,
        qualification=data.qualification,
        hashed_password=hash_password(data.password),
        is_active=True
    )
    
    db.add(new_staff)
    db.commit()
    db.refresh(new_staff)
    
    return {
        "status": "success",
        "message": f"Staff member '{new_staff.name}' created successfully.",
        "staff": {
            "id": new_staff.id,
            "name": new_staff.name,
            "email": new_staff.email,
            "role": new_staff.role.value
        }
    }

