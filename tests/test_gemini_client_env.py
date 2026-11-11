import pytest

from app.llm.gemini_client import GeminiClient


def test_erro_claro_quando_falta_gemini_model(monkeypatch):
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "chave-fake-de-teste")
    with pytest.raises(RuntimeError) as erro:
        GeminiClient()
    assert "GEMINI_MODEL" in str(erro.value)
    assert ".env" in str(erro.value)
    assert "chave-fake-de-teste" not in str(erro.value)


def test_erro_claro_quando_falta_gemini_api_key(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL", "modelo-fake-de-teste")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(RuntimeError) as erro:
        GeminiClient()
    assert "GEMINI_API_KEY" in str(erro.value)
    assert ".env" in str(erro.value)
