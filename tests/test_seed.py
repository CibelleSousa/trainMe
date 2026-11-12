from sqlmodel import SQLModel, create_engine, select
from sqlmodel import Session as DbSession

import app.db as db_mod
import app.seed as seed_mod
from app.models import ExerciseLog, SetLog
from app.models import Session as SessionModel


def db_temporario(monkeypatch, tmp_path):
    caminho = tmp_path / "seed_teste.db"
    engine = create_engine(f"sqlite:///{caminho}")
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(db_mod, "engine", engine)
    return engine


def test_seed_carrega_sessoes_e_series(monkeypatch, tmp_path):
    db_temporario(monkeypatch, tmp_path)

    resumo = seed_mod.seed()

    assert resumo["sessoes_criadas"] > 0
    assert resumo["series_criadas"] > 0

    with DbSession(db_mod.engine) as db:
        total_sessoes = len(db.exec(select(SessionModel)).all())
        total_series = len(db.exec(select(SetLog)).all())
    assert total_sessoes == resumo["sessoes_criadas"]
    assert total_series == resumo["series_criadas"]


def test_seed_e_idempotente_nao_duplica_ao_rodar_de_novo(monkeypatch, tmp_path):
    db_temporario(monkeypatch, tmp_path)

    primeiro = seed_mod.seed()
    segundo = seed_mod.seed()

    assert segundo["sessoes_criadas"] == 0
    assert segundo["exercicios_criados"] == 0
    assert segundo["series_criadas"] == 0

    with DbSession(db_mod.engine) as db:
        total_sessoes = len(db.exec(select(SessionModel)).all())
        total_series = len(db.exec(select(SetLog)).all())
    assert total_sessoes == primeiro["sessoes_criadas"]
    assert total_series == primeiro["series_criadas"]
