import pytest

from app.extract import extract
from app.llm.ollama_client import OllamaClient

pytestmark = pytest.mark.integration


def test_fumaca_ollama_qwen3():
    client = OllamaClient()
    resultado = extract(client, "supino reto 3x10 com 80")
    assert resultado.entries
    assert resultado.entries[0].sets
