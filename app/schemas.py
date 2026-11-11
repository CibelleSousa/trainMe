from typing import Literal

from pydantic import BaseModel

SetFlag = Literal["failure", "dropset", "warmup"]


class SetEntry(BaseModel):
    weight_kg: float | None = None
    reps: int
    flag: SetFlag | None = None


class ExerciseEntry(BaseModel):
    exercise_raw: str
    sets: list[SetEntry]


class ExtractionResult(BaseModel):
    entries: list[ExerciseEntry]
    needs_confirmation: bool = False
