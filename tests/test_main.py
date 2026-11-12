from fastapi.testclient import TestClient

import app.main as main_mod


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
