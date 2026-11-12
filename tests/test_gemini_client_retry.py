import pytest
from google.genai.errors import ClientError, ServerError

from app.llm.gemini_client import GeminiClient


def _client_com_chamadas(respostas):
    """respostas: lista de exceções ou valores-texto a devolver em sequência."""

    class FakeModels:
        def __init__(self):
            self.chamadas = 0

        def generate_content(self, model, contents, config):
            self.chamadas += 1
            item = respostas[self.chamadas - 1]
            if isinstance(item, Exception):
                raise item
            return type("Resp", (), {"text": item})()

    class FakeClient:
        def __init__(self):
            self.models = FakeModels()

    return FakeClient()


@pytest.fixture(autouse=True)
def _sem_env_real(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL", "modelo-fake")
    monkeypatch.setenv("GEMINI_API_KEY", "chave-fake")


@pytest.fixture(autouse=True)
def _sem_espera(monkeypatch):
    monkeypatch.setattr("app.llm.gemini_client.time.sleep", lambda s: None)


def test_tenta_de_novo_em_503(monkeypatch):
    client = GeminiClient()
    fake = _client_com_chamadas([ServerError(503, {}), '{"ok": true}'])
    monkeypatch.setattr(client, "_client", fake)

    resultado = client.extract("texto", {})

    assert resultado == {"ok": True}
    assert fake.models.chamadas == 2


def test_tenta_de_novo_em_500_e_504(monkeypatch):
    client = GeminiClient()
    fake = _client_com_chamadas([ServerError(500, {}), ServerError(504, {}), '{"ok": true}'])
    monkeypatch.setattr(client, "_client", fake)

    resultado = client.extract("texto", {})

    assert resultado == {"ok": True}
    assert fake.models.chamadas == 3


def test_ate_5_tentativas_depois_propaga(monkeypatch):
    client = GeminiClient()
    fake = _client_com_chamadas([ServerError(503, {})] * 5)
    monkeypatch.setattr(client, "_client", fake)

    with pytest.raises(ServerError):
        client.extract("texto", {})

    assert fake.models.chamadas == 5


def test_nao_tenta_de_novo_em_erro_sem_codigo_de_retry(monkeypatch):
    client = GeminiClient()
    fake = _client_com_chamadas([ClientError(400, {}), '{"ok": true}'])
    monkeypatch.setattr(client, "_client", fake)

    with pytest.raises(ClientError):
        client.extract("texto", {})

    assert fake.models.chamadas == 1
