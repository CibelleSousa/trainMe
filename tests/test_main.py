from datetime import date

from fastapi.testclient import TestClient
from sqlmodel import SQLModel, create_engine

import app.db as db_mod
import app.main as main_mod
from app.agent import log_sets


class AgentFalso:
    def __init__(self, resposta: str):
        self._resposta = resposta
        self.chamadas = []

    def handle_message(self, db, text, data, com_personal=False):
        self.chamadas.append((text, data, com_personal))
        return self._resposta


def test_post_chat_devolve_reply_do_agente(monkeypatch):
    agente_falso = AgentFalso("Salvei seu treino.")
    monkeypatch.setattr(main_mod, "_agent", agente_falso)

    client = TestClient(main_mod.app)
    resposta = client.post("/chat", json={"text": "supino 3x10 com 80"})

    assert resposta.status_code == 200
    assert resposta.json() == {"reply": "Salvei seu treino."}
    assert agente_falso.chamadas[0][0] == "supino 3x10 com 80"


def test_post_chat_aceita_com_personal_e_data(monkeypatch):
    agente_falso = AgentFalso("ok")
    monkeypatch.setattr(main_mod, "_agent", agente_falso)

    client = TestClient(main_mod.app)
    client.post("/chat", json={"text": "treino", "date": "2026-11-11", "com_personal": True})

    _texto, data, com_personal = agente_falso.chamadas[0]
    assert com_personal is True
    assert str(data) == "2026-11-11"


def db_temporario(monkeypatch, tmp_path):
    caminho = tmp_path / "teste.db"
    engine = create_engine(f"sqlite:///{caminho}")
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(db_mod, "engine", engine)
    return engine


def test_pagina_inicial_serve_html(monkeypatch, tmp_path):
    db_temporario(monkeypatch, tmp_path)
    with TestClient(main_mod.app) as client:
        resposta = client.get("/")
    assert resposta.status_code == 200
    assert "text/html" in resposta.headers["content-type"]
    assert "Gravar" in resposta.text


def test_export_csv_devolve_cabecalho_e_series(monkeypatch, tmp_path):
    engine = db_temporario(monkeypatch, tmp_path)
    with db_mod.get_session() as db:
        normalizado = {
            "entries": [
                {"exercise_raw": "supino", "exercise_slug": "supino_reto_barra", "sets": [{"weight_kg": 80.0, "reps": 10, "flag": None}]}
            ],
            "needs_confirmation": False,
        }
        log_sets(db, date(2026, 11, 11), "supino 1x10 com 80", False, normalizado)

    with TestClient(main_mod.app) as client:
        resposta = client.get("/export.csv")

    assert resposta.status_code == 200
    assert resposta.headers["content-type"].startswith("text/csv")
    linhas = resposta.text.strip().splitlines()
    cabecalho = linhas[0].split(",")
    assert cabecalho == ["date", "exercise_slug", "exercise_raw", "set_number", "weight_kg", "reps", "flag", "com_personal"]
    colunas_dados = linhas[1].split(",")
    assert len(colunas_dados) == len(cabecalho)
    assert colunas_dados[cabecalho.index("exercise_slug")] == "supino_reto_barra"
    assert colunas_dados[cabecalho.index("weight_kg")] == "80.0"
    assert colunas_dados[cabecalho.index("com_personal")] == "False"


def test_history_devolve_series_ordenadas_por_data(monkeypatch, tmp_path):
    engine = db_temporario(monkeypatch, tmp_path)
    with db_mod.get_session() as db:
        for dia, peso in [(9, 70.0), (11, 80.0), (10, 75.0)]:
            normalizado = {
                "entries": [
                    {"exercise_raw": "supino", "exercise_slug": "supino_reto_barra", "sets": [{"weight_kg": peso, "reps": 10, "flag": None}]}
                ],
                "needs_confirmation": False,
            }
            log_sets(db, date(2026, 11, dia), "x", False, normalizado)

    with TestClient(main_mod.app) as client:
        resposta = client.get("/history/supino_reto_barra")

    assert resposta.status_code == 200
    pesos = [h["sets"][0]["weight_kg"] for h in resposta.json()]
    assert pesos == [70.0, 75.0, 80.0]
