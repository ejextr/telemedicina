from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: int
    role: str
    exp: int


class User(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: str
    created_at: datetime
    specialty: Optional[str] = None
    experience_years: Optional[int] = None
    birth_date: Optional[datetime] = None
    medical_history: Optional[str] = None
    allergies: Optional[str] = None
    avatar: Optional[str] = None


class UserBase(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: str
    created_at: datetime


class UserProfileUpdate(BaseModel):
    specialty: Optional[str] = None
    experience_years: Optional[int] = None
    birth_date: Optional[datetime] = None
    medical_history: Optional[str] = None
    allergies: Optional[str] = None
    avatar: Optional[str] = None


class UserProfileResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: str
    specialty: Optional[str]
    experience_years: Optional[int]
    birth_date: Optional[datetime]
    medical_history: Optional[str]
    allergies: Optional[str]
    avatar: Optional[str]
    created_at: datetime


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserUpdateStatus(BaseModel):
    is_on_guard: bool
    is_accepting: bool


class DoctorStatusResponse(BaseModel):
    doctor_id: int
    is_on_guard: bool
    is_accepting: bool
    updated_at: datetime


class DoctorPublic(BaseModel):
    id: int
    name: str
    specialty: Optional[str]
    experience_years: Optional[int]
    is_on_guard: bool
    is_accepting: bool


class WaitingRoomCreate(BaseModel):
    doctor_id: int
    note: Optional[str] = None


class WaitingRoomPublic(BaseModel):
    id: int
    doctor_id: int
    doctor_name: str
    patient_id: int
    patient_name: str
    note: Optional[str]
    status: str
    call_status: str
    created_at: datetime
    updated_at: datetime


class MessageCreate(BaseModel):
    content: str


class MessagePublic(BaseModel):
    id: int
    room_id: int
    sender_id: int
    content: str


class RatingCreate(BaseModel):
    doctor_id: int
    rating: int
    comment: Optional[str] = None


class RatingPublic(BaseModel):
    id: int
    patient_id: int
    doctor_id: int
    rating: int
    comment: Optional[str]
    created_at: datetime
    created_at: datetime
