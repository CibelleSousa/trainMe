from sqlmodel import Session as DbSession
from sqlmodel import SQLModel, create_engine

DATABASE_URL = "sqlite:///treino.db"

engine = create_engine(DATABASE_URL)


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)


def get_session() -> DbSession:
    return DbSession(engine)
