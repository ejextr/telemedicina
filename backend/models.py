from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field, Relationship


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    email: str = Field(unique=True, index=True)
    hashed_password: str
    role: str = Field(index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Profile fields
    specialty: Optional[str] = None  # For doctors
    experience_years: Optional[int] = None  # For doctors
    birth_date: Optional[datetime] = None  # For patients
    medical_history: Optional[str] = None  # For patients
    allergies: Optional[str] = None  # For patients
    avatar: Optional[str] = None  # URL or path to avatar image

    doctor_status: Optional["DoctorStatus"] = Relationship(back_populates="doctor")


class DoctorStatus(SQLModel, table=True):
    doctor_id: int = Field(default=None, primary_key=True, foreign_key="user.id")
    is_on_guard: bool = Field(default=False)
    is_accepting: bool = Field(default=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    doctor: User = Relationship(back_populates="doctor_status")


class WaitingRoom(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    doctor_id: int = Field(foreign_key="user.id")
    patient_id: int = Field(foreign_key="user.id")
    note: Optional[str] = None
    status: str = Field(default="waiting", index=True)
    call_status: str = Field(default="none", index=True)  # none, invited, in_call, ended
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Message(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    room_id: int = Field(foreign_key="waitingroom.id", index=True)
    sender_id: int = Field(foreign_key="user.id")
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class Rating(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    patient_id: int = Field(foreign_key="user.id")
    doctor_id: int = Field(foreign_key="user.id")
    rating: int = Field(ge=1, le=5)
    comment: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
