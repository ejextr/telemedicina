from datetime import datetime, timedelta
from typing import Optional
import os

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from jwt import PyJWTError
from passlib.context import CryptContext
from sqlmodel import Session, select

from .database import get_session
from .models import User, DoctorStatus

SECRET_KEY = "secret"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24
REFRESH_TOKEN_EXPIRE_DAYS = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(*, data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    # Temporarily remove exp to test if that's causing the issue
    # if expires_delta:
    #     expire = datetime.utcnow() + expires_delta
    # else:
    #     expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    # to_encode.update({"exp": expire.timestamp()})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(*, data: dict) -> str:
    to_encode = data.copy()
    # Temporarily remove exp to test if that's causing the issue
    # expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    # to_encode.update({"exp": expire.timestamp()})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_user_by_email(session: Session, email: str) -> Optional[User]:
    return session.exec(select(User).where(User.email == email)).first()


def get_current_user(token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    # Detailed debug logging to investigate 401 on /users/me
    try:
        print(f"[auth] get_current_user: raw token: {token[:30]}...")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": False})
        print(f"[auth] get_current_user: decoded payload: {payload}")
        user_id_raw = payload.get("sub")
        role: str = payload.get("role")
        if user_id_raw is None or role is None:
            print("[auth] get_current_user: missing sub or role")
            raise credentials_exception
        user_id = int(user_id_raw)

    except (PyJWTError, ValueError) as e:
        print(f"[auth] get_current_user: token decode error: {e}")
        raise credentials_exception

    user = session.get(User, user_id)
    if user is None:
        raise credentials_exception
    return user


def require_role(required_role: str):
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role != required_role:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user

    return checker


def ensure_doctor_status(session: Session, doctor_id: int) -> DoctorStatus:
    status_record = session.get(DoctorStatus, doctor_id)
    if not status_record:
        status_record = DoctorStatus(doctor_id=doctor_id)
        session.add(status_record)
        session.commit()
        session.refresh(status_record)
    return status_record


def refresh_access_token(token: str) -> str:
    """Refresh an access token using refresh token"""
    try:
        print(f"[auth] refresh_access_token: raw token: {token[:30]}...")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": False})
        print(f"[auth] refresh_access_token: decoded payload: {payload}")
        user_id = payload.get("sub")
        role = payload.get("role")
        if user_id and role:
            # Create a new access token with fresh expiration
            new_token = create_access_token(data={"sub": str(user_id), "role": role})
            print(f"[auth] refresh_access_token: new token generated")
            return new_token
    except PyJWTError as e:
        print(f"[auth] refresh_access_token: decode error: {e}")
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
