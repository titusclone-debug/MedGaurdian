"""Authentication and Authorization — JWT + RBAC."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.database import Staff, UserRole

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
