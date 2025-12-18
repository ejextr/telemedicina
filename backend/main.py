from datetime import datetime
from pathlib import Path
from typing import List

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, select

from . import schemas
from .database import get_session
from .models import Rating, User
from .auth import (
    create_access_token,
    create_refresh_token,
    ensure_doctor_status,
    get_current_user,
    get_password_hash,
    get_user_by_email,
    oauth2_scheme,
    refresh_access_token,
    require_role,
    verify_password,
)
from .database import get_session, init_db
from .models import Message, User, WaitingRoom

app = FastAPI(title="MedicApp Backend")
BASE_DIR = Path(__file__).resolve().parent.parent

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def create_default_users():
    """Create default test users on startup"""
    session = next(get_session())
    try:
        # Create patient user
        patient_email = "paciente@gmail.com"
        if not session.exec(select(User).where(User.email == patient_email)).first():
            patient = User(
                name="Paciente de Prueba",
                email=patient_email,
                hashed_password=get_password_hash("12345679"),
                role="patient"
            )
            session.add(patient)
            session.commit()

        # Create doctor user
        doctor_email = "medico@gmail.com"
        if not session.exec(select(User).where(User.email == doctor_email)).first():
            doctor = User(
                name="Médico de Prueba",
                email=doctor_email,
                hashed_password=get_password_hash("12345679"),
                role="doctor",
                specialty="Medicina General",
                experience_years=10
            )
            session.add(doctor)
            session.commit()
            # Create doctor status
            ensure_doctor_status(session, doctor.id)

        print("Default users created successfully")
    except Exception as e:
        print(f"Error creating default users: {e}")
    finally:
        session.close()


@app.on_event("startup")
def startup_event():
    init_db()
    create_default_users()


def waiting_room_to_schema(room: WaitingRoom, session: Session) -> schemas.WaitingRoomPublic:
    doctor = session.get(User, room.doctor_id)
    patient = session.get(User, room.patient_id)
    return schemas.WaitingRoomPublic(
        id=room.id,
        doctor_id=room.doctor_id,
        doctor_name=doctor.name if doctor else "",
        patient_id=room.patient_id,
        patient_name=patient.name if patient else "",
        note=room.note,
        status=room.status,
        call_status=room.call_status,
        created_at=room.created_at,
        updated_at=room.updated_at,
    )





@app.get("/", response_class=FileResponse)
def read_root() -> FileResponse:
    return FileResponse(BASE_DIR / "index.html")


app.mount(
    "/static",
    StaticFiles(directory=BASE_DIR, html=False),
    name="static",
)


@app.post("/auth/register", response_model=schemas.UserBase, status_code=status.HTTP_201_CREATED)
def register_user(data: schemas.UserCreate, session: Session = Depends(get_session)):
    existing = get_user_by_email(session, data.email)
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registrado")

    if data.role not in {"patient", "doctor"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Rol invalido")

    user = User(
        name=data.name,
        email=data.email,
        hashed_password=get_password_hash(data.password),
        role=data.role,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    if user.role == "doctor":
        ensure_doctor_status(session, user.id)

    return user


@app.post("/auth/login", response_model=schemas.Token)
def login(credentials: schemas.LoginRequest, session: Session = Depends(get_session)):
    user = get_user_by_email(session, credentials.email)
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales invalidas")

    access_token = create_access_token(data={"sub": str(user.id), "role": user.role})
    refresh_token = create_refresh_token(data={"sub": str(user.id), "role": user.role})
    print(f"[main] login: generated access_token: {access_token[:30]}...")
    return schemas.Token(access_token=access_token, refresh_token=refresh_token)


@app.post("/auth/refresh", response_model=schemas.Token)
def refresh_token(token: str = Depends(oauth2_scheme)):
    print(f"[main] refresh_token: incoming token: {token[:30]}...")
    new_token = refresh_access_token(token)
    print(f"[main] refresh_token: new_token: {new_token[:30]}...")
    return schemas.Token(access_token=new_token)


@app.get("/debug/echo-auth")
def debug_echo_auth(request: Request):
    auth = request.headers.get("authorization")
    cookies = dict(request.cookies)
    result = {"authorization": auth, "cookies": cookies}
    # Attempt to decode the bearer token for extra info
    if auth and auth.lower().startswith("bearer "):
        token = auth.split(" ", 1)[1]
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": False})
            result["decoded"] = payload
        except Exception as e:
            result["decoded_error"] = str(e)
    return result


@app.get("/")
def root():
    return {"message": "MedicApp API", "status": "running"}

@app.get("/favicon.ico")
def favicon():
    # Return empty response for favicon to avoid 404
    from fastapi.responses import Response
    return Response(content="", media_type="image/x-icon")

@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/users/me", response_model=schemas.User)
def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user


@app.get("/users/me/profile", response_model=schemas.UserProfileResponse)
def read_current_user_profile(current_user: User = Depends(get_current_user)):
    return current_user


@app.put("/users/me/profile", response_model=schemas.UserProfileResponse)
def update_current_user_profile(
    profile_update: schemas.UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    update_data = profile_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(current_user, field, value)
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    return current_user


@app.get("/doctors", response_model=List[schemas.DoctorPublic])
def list_doctors(session: Session = Depends(get_session)):
    doctors = session.exec(select(User).where(User.role == "doctor")).all()
    result = []
    for doctor in doctors:
        status_record = ensure_doctor_status(session, doctor.id)
        result.append(
            schemas.DoctorPublic(
                id=doctor.id,
                name=doctor.name,
                specialty=doctor.specialty,
                experience_years=doctor.experience_years,
                is_on_guard=status_record.is_on_guard,
                is_accepting=status_record.is_accepting,
            )
        )
    return result


@app.get("/doctor/status", response_model=schemas.DoctorStatusResponse)
def get_doctor_status(
    current_user: User = Depends(require_role("doctor")),
    session: Session = Depends(get_session),
):
    status_record = ensure_doctor_status(session, current_user.id)
    return schemas.DoctorStatusResponse(
        doctor_id=current_user.id,
        is_on_guard=status_record.is_on_guard,
        is_accepting=status_record.is_accepting,
        updated_at=status_record.updated_at,
    )


@app.post("/doctor/status", response_model=schemas.DoctorStatusResponse)
def update_doctor_status(
    payload: schemas.UserUpdateStatus,
    current_user: User = Depends(require_role("doctor")),
    session: Session = Depends(get_session),
):
    status_record = ensure_doctor_status(session, current_user.id)
    status_record.is_on_guard = payload.is_on_guard
    status_record.is_accepting = payload.is_accepting
    status_record.updated_at = datetime.utcnow()
    session.add(status_record)
    session.commit()
    session.refresh(status_record)
    return schemas.DoctorStatusResponse(
        doctor_id=current_user.id,
        is_on_guard=status_record.is_on_guard,
        is_accepting=status_record.is_accepting,
        updated_at=status_record.updated_at,
    )


@app.post("/waiting-room", response_model=schemas.WaitingRoomPublic, status_code=status.HTTP_201_CREATED)
def create_waiting_room(
    payload: schemas.WaitingRoomCreate,
    current_user: User = Depends(require_role("patient")),
    session: Session = Depends(get_session),
):
    doctor = session.get(User, payload.doctor_id)
    if not doctor or doctor.role != "doctor":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medico no encontrado")

    ensure_doctor_status(session, doctor.id)

    existing = session.exec(
        select(WaitingRoom)
        .where(WaitingRoom.doctor_id == doctor.id)
        .where(WaitingRoom.patient_id == current_user.id)
        .where(WaitingRoom.status.in_(["waiting", "active"]))
    ).first()

    if existing:
        if payload.note:
            existing.note = payload.note
            existing.updated_at = datetime.utcnow()
            session.add(existing)
            session.commit()
            session.refresh(existing)
        return waiting_room_to_schema(existing, session)

    room = WaitingRoom(
        doctor_id=doctor.id,
        patient_id=current_user.id,
        note=payload.note,
        status="waiting",
    )
    session.add(room)
    session.commit()
    session.refresh(room)
    return waiting_room_to_schema(room, session)


@app.get("/patient/waiting-rooms", response_model=List[schemas.WaitingRoomPublic])
def list_patient_rooms(
    current_user: User = Depends(require_role("patient")),
    session: Session = Depends(get_session),
):
    rooms = session.exec(select(WaitingRoom).where(WaitingRoom.patient_id == current_user.id)).all()
    return [waiting_room_to_schema(room, session) for room in rooms]


@app.get("/doctor/waiting-rooms", response_model=List[schemas.WaitingRoomPublic])
def list_doctor_rooms(
    current_user: User = Depends(require_role("doctor")),
    session: Session = Depends(get_session),
):
    rooms = session.exec(select(WaitingRoom).where(WaitingRoom.doctor_id == current_user.id)).all()
    return [waiting_room_to_schema(room, session) for room in rooms]


@app.get("/waiting-room/{room_id}/messages", response_model=List[schemas.MessagePublic])
def list_room_messages(
    room_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    room = session.get(WaitingRoom, room_id)
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sala no encontrada")
    if current_user.id not in {room.patient_id, room.doctor_id}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sin acceso a la sala")

    messages = session.exec(select(Message).where(Message.room_id == room_id).order_by(Message.created_at)).all()
    return [
        schemas.MessagePublic(
            id=msg.id,
            room_id=msg.room_id,
            sender_id=msg.sender_id,
            content=msg.content,
            created_at=msg.created_at,
        )
        for msg in messages
    ]


@app.post("/waiting-room/{room_id}/messages", response_model=schemas.MessagePublic, status_code=status.HTTP_201_CREATED)
def send_message(
    room_id: int,
    payload: schemas.MessageCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    room = session.get(WaitingRoom, room_id)
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sala no encontrada")
    if current_user.id not in {room.patient_id, room.doctor_id}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sin acceso a la sala")

    message = Message(room_id=room_id, sender_id=current_user.id, content=payload.content)
    session.add(message)

    room.status = "active"
    room.updated_at = datetime.utcnow()
    session.add(room)

    session.commit()
    session.refresh(message)

    return schemas.MessagePublic(
        id=message.id,
        room_id=message.room_id,
        sender_id=message.sender_id,
        content=message.content,
        created_at=message.created_at,
    )


@app.put("/waiting-room/{room_id}/start-call", response_model=schemas.WaitingRoomPublic)
def start_call(room_id: int, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    room = session.get(WaitingRoom, room_id)
    if not room or room.doctor_id != current_user.id:
        raise HTTPException(status_code=404, detail="Sala no encontrada")
    room.call_status = "invited"
    room.updated_at = datetime.utcnow()
    session.add(room)
    session.commit()
    session.refresh(room)
    return waiting_room_to_schema(room, session)


@app.put("/waiting-room/{room_id}/respond-call", response_model=schemas.WaitingRoomPublic)
def respond_call(room_id: int, accept: bool, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    room = session.get(WaitingRoom, room_id)
    if not room or room.patient_id != current_user.id:
        raise HTTPException(status_code=404, detail="Sala no encontrada")
    room.call_status = "in_call" if accept else "ended"
    room.updated_at = datetime.utcnow()
    session.add(room)
    session.commit()
    session.refresh(room)
    return waiting_room_to_schema(room, session)


@app.post("/ratings", response_model=schemas.RatingPublic)
def create_rating(
    rating_data: schemas.RatingCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    rating = Rating(
        patient_id=current_user.id,
        doctor_id=rating_data.doctor_id,
        rating=rating_data.rating,
        comment=rating_data.comment
    )
    session.add(rating)
    session.commit()
    session.refresh(rating)
    return rating


@app.get("/doctors/{doctor_id}/ratings", response_model=List[schemas.RatingPublic])
def get_doctor_ratings(doctor_id: int, session: Session = Depends(get_session)):
    ratings = session.exec(select(Rating).where(Rating.doctor_id == doctor_id)).all()
    return ratings

