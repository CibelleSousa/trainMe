from datetime import date

from sqlmodel import SQLModel, create_engine, select
from sqlmodel import Session as DbSession

from app.models import ExerciseLog, Session, SetLog


def make_engine():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    return engine


def test_cria_tabelas():
    engine = make_engine()
    assert SQLModel.metadata.tables.keys() >= {"session", "exerciselog", "setlog"}


def test_grava_sessao_exercicio_e_series():
    engine = make_engine()
    with DbSession(engine) as db:
        sessao = Session(date=date(2026, 11, 11), raw_text="supino 4x8 com 80")
        db.add(sessao)
        db.commit()
        db.refresh(sessao)

        exercicio = ExerciseLog(
            session_id=sessao.id,
            exercise_raw="supino",
            exercise_slug="supino_reto_barra",
        )
        db.add(exercicio)
        db.commit()
        db.refresh(exercicio)

        for i in range(1, 5):
            db.add(SetLog(exercise_log_id=exercicio.id, set_number=i, weight_kg=80, reps=8))
        db.commit()

        series = db.exec(
            select(SetLog).where(SetLog.exercise_log_id == exercicio.id)
        ).all()
        assert len(series) == 4
