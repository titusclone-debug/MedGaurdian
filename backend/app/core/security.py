"""Security helpers for authentication and password handling."""
from datetime import datetime, timedelta
from typing import Any

import bcrypt
from jose import jwt

from app.core.config import settings


def validate_password_strength(password: str) -> None:
    """Apply the minimum server-side policy for newly issued credentials."""
    if len(password) < 12:
        raise ValueError("Password must contain at least 12 characters.")
    if not any(character.islower() for character in password):
        raise ValueError("Password must contain a lowercase letter.")
    if not any(character.isupper() for character in password):
        raise ValueError("Password must contain an uppercase letter.")
    if not any(character.isdigit() for character in password):
        raise ValueError("Password must contain a number.")


def hash_password(password: str) -> str:
    """Hash a plaintext password using a production-safe adaptive algorithm."""
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a stored password hash securely."""
    try:
        plain_bytes = plain_password.encode("utf-8")
        hashed_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(plain_bytes, hashed_bytes)
    except Exception:
        return False


def create_access_token(subject: str, claims: dict[str, Any]) -> str:
    """Create a signed JWT access token."""
    token_data = {
        "sub": subject,
        **claims,
        "exp": datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(token_data, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
