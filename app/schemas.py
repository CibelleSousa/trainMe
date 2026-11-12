from typing import Literal

from pydantic import BaseModel

SetFlag = Literal["failure", "dropset", "warmup"]


class SetEntry(BaseModel):
    weight_kg: float | None = None
    reps: int
    por_lado: bool = False
    rir: int | None = None
    flag: SetFlag | None = None


class ExerciseEntry(BaseModel):
    exercise_raw: str
    sets: list[SetEntry]


class ExtractionResult(BaseModel):
    entries: list[ExerciseEntry]
    needs_confirmation: bool = False
