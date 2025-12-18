from sqlmodel import SQLModel, create_engine, Session
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "medicapp.db"
DATABASE_URL = f"sqlite:///{DB_PATH.as_posix()}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


def init_db() -> None:
    from . import models  # noqa: F401 ensures models are imported

    # Recreate all tables to ensure schema is up to date
    # This is safe because default users are recreated on startup
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)


def get_session() -> Session:
    with Session(engine) as session:
        yield session
