import pytest
from pydantic import ValidationError

from app.schemas import ExerciseEntry, ExtractionResult, SetEntry


def test_set_entry_aceita_peso_corporal():
    s = SetEntry(weight_kg=None, reps=12)
    assert s.weight_kg is None
    assert s.flag is None


def test_set_entry_flag_invalido_rejeitado():
    with pytest.raises(ValidationError):
        SetEntry(weight_kg=10, reps=10, flag="invalido")


def test_exercise_entry_com_varias_series():
    e = ExerciseEntry(
        exercise_raw="supino",
        sets=[SetEntry(weight_kg=80, reps=8) for _ in range(4)],
    )
    assert len(e.sets) == 4


def test_extraction_result_default_needs_confirmation_false():
    r = ExtractionResult(entries=[])
    assert r.needs_confirmation is False


def test_extraction_result_sem_dados_precisa_confirmacao():
    r = ExtractionResult(entries=[], needs_confirmation=True)
    assert r.entries == []
    assert r.needs_confirmation is True
