from datetime import date

from sqlmodel import SQLModel, create_engine, select
from sqlmodel import Session as DbSession

import app.agent as agent_mod
from app.agent import Agent, get_history, log_sets
from app.models import ExerciseLog, SetLog


def db_memoria():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    return DbSession(engine)


class ClientFalso:
    def __init__(self, respostas=None, explode_na_chamada=None):
        self._respostas = list(respostas or [])
        self.chamadas = []
        self._explode_na_chamada = explode_na_chamada

    def extract(self, text: str, schema: dict) -> dict:
        self.chamadas.append((text, schema))
        if self._explode_na_chamada == len(self.chamadas):
            raise RuntimeError("falha simulada do provider")
        return self._respostas.pop(0)


def extracao_supino():
    return {
        "entries": [{"exercise_raw": "supino", "sets": [{"weight_kg": 80, "reps": 10, "flag": None}] * 3}],
        "needs_confirmation": False,
    }


def test_log_sets_grava_sessao_exercicio_e_series():
    db = db_memoria()
    normalizado = {
        "entries": [
            {
                "exercise_raw": "supino",
                "exercise_slug": "supino_reto_barra",
                "sets": [{"weight_kg": 80.0, "reps": 10, "flag": None}] * 3,
            }
        ],
        "needs_confirmation": False,
    }
    resumo = log_sets(db, date(2026, 11, 11), "supino 3x10 com 80", False, normalizado)
    assert resumo["exercicios"][0]["slug"] == "supino_reto_barra"
    assert resumo["exercicios"][0]["n_series"] == 3
    assert len(db.exec(select(SetLog)).all()) == 3


def test_get_history_ordena_por_data_e_aplica_limite():
    db = db_memoria()
    normalizado = lambda peso: {
        "entries": [
            {"exercise_raw": "supino", "exercise_slug": "supino_reto_barra", "sets": [{"weight_kg": peso, "reps": 10, "flag": None}]}
        ],
        "needs_confirmation": False,
    }
    log_sets(db, date(2026, 11, 9), "a", False, normalizado(70))
    log_sets(db, date(2026, 11, 11), "b", False, normalizado(80))
    log_sets(db, date(2026, 11, 10), "c", False, normalizado(75))

    historico = get_history(db, "supino_reto_barra")
    pesos = [h["sets"][0]["weight_kg"] for h in historico]
    assert pesos == [70, 75, 80]


def test_agent_salva_e_compoe_mensagem_so_com_dados_das_ferramentas():
    db = db_memoria()
    primary = ClientFalso(respostas=[extracao_supino(), {"mensagem": "Salvei seu supino. Próxima: 82.5kg."}])
    fallback = ClientFalso()
    agente = Agent(primary=primary, fallback=fallback)

    resposta = agente.handle_message(db, "supino 3x10 com 80", date(2026, 11, 11))

    assert resposta == "Salvei seu supino. Próxima: 82.5kg."
    assert len(db.exec(select(ExerciseLog)).all()) == 1

    prompt_final, schema_final = primary.chamadas[1]
    assert schema_final == agent_mod.MENSAGEM_SCHEMA
    assert "log_sets" in prompt_final


def test_agent_needs_confirmation_pergunta_sem_gravar():
    db = db_memoria()
    extracao = {
        "entries": [{"exercise_raw": "aparelho inexistente", "sets": [{"weight_kg": 10, "reps": 10, "flag": None}]}],
        "needs_confirmation": False,
    }
    primary = ClientFalso(respostas=[extracao])
    fallback = ClientFalso()
    agente = Agent(primary=primary, fallback=fallback)

    resposta = agente.handle_message(db, "fiz um negócio novo com 10, 10 reps", date(2026, 11, 11))

    assert "aparelho inexistente" in resposta
    assert db.exec(select(ExerciseLog)).all() == []
    assert len(primary.chamadas) == 1  # não chamou a LLM de novo pra compor mensagem


def test_agent_usa_fallback_quando_primary_falha_na_extracao():
    db = db_memoria()
    primary = ClientFalso(explode_na_chamada=1)
    fallback = ClientFalso(respostas=[extracao_supino(), {"mensagem": "ok via fallback"}])
    agente = Agent(primary=primary, fallback=fallback)

    resposta = agente.handle_message(db, "supino 3x10 com 80", date(2026, 11, 11))

    assert resposta == "ok via fallback"
    assert len(db.exec(select(ExerciseLog)).all()) == 1


def test_agent_respeita_no_maximo_3_passos_com_varios_exercicios(monkeypatch):
    db = db_memoria()
    extracao_multi = {
        "entries": [
            {"exercise_raw": "supino", "sets": [{"weight_kg": 80, "reps": 10, "flag": None}]},
            {"exercise_raw": "remada serrote", "sets": [{"weight_kg": 40, "reps": 10, "flag": None}]},
        ],
        "needs_confirmation": False,
    }
    primary = ClientFalso(respostas=[extracao_multi, {"mensagem": "ok"}])
    fallback = ClientFalso()

    chamadas_history = []
    chamadas_suggest = []
    monkeypatch.setattr(agent_mod, "get_history", lambda db, slug, limit=10: (chamadas_history.append(slug), [])[1])
    monkeypatch.setattr(agent_mod, "suggest_next_tool", lambda historico, **kw: (chamadas_suggest.append(historico), {})[1])

    agente = Agent(primary=primary, fallback=fallback)
    agente.handle_message(db, "supino 1x10 com 80, remada serrote 1x10 com 40", date(2026, 11, 11))

    assert len(chamadas_history) == 1
    assert len(chamadas_suggest) == 1
