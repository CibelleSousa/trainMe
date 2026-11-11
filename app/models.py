from datetime import date as date_type
from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


class Session(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    date: date_type
    raw_text: str
    com_personal: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ExerciseLog(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="session.id")
    exercise_raw: str
    exercise_slug: str | None = None
    needs_confirmation: bool = False


class SetLog(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    exercise_log_id: int = Field(foreign_key="exerciselog.id")
    set_number: int
    weight_kg: float | None = None
    reps: int
    flag: str | None = None
