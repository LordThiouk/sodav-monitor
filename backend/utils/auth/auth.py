"""Authentication utilities for SODAV Monitor."""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from backend.core.config.settings import get_settings
from backend.models.database import get_db
from backend.models.models import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

settings = get_settings()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate a password hash."""
    return pwd_context.hash(password)


def create_access_token(
    data: dict, expires_delta: Optional[timedelta] = None, settings_override: Optional[dict] = None
) -> str:
    """Create an access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": int(expire.timestamp())})

    # Use settings override if provided, otherwise use global settings
    if settings_override:
        secret_key = settings_override.get("SECRET_KEY") or settings_override.get("JWT_SECRET_KEY")
        algorithm = settings_override["ALGORITHM"]
    else:
        secret_key = settings.SECRET_KEY
        algorithm = settings.ALGORITHM

    if not secret_key:
        raise ValueError("No secret key provided")

    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=algorithm)
    return encoded_jwt


async def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
    settings_override: Optional[dict] = None,
) -> User:
    """Get the current user from a JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Use settings override if provided, otherwise use global settings
        if settings_override:
            secret_key = settings_override.get("SECRET_KEY") or settings_override.get(
                "JWT_SECRET_KEY"
            )
            algorithm = settings_override["ALGORITHM"]
        else:
            secret_key = settings.SECRET_KEY
            algorithm = settings.ALGORITHM

        if not secret_key:
            raise ValueError("No secret key provided")

        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    return user
