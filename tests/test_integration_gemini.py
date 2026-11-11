import os

import pytest

from app.extract import extract
from app.llm.gemini_client import GeminiClient

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not os.environ.get("GEMINI_API_KEY"), reason="GEMINI_API_KEY não configurada"),
]


def test_fumaca_gemini():
    client = GeminiClient()
    resultado = extract(client, "supino reto 3x10 com 80")
    assert resultado.entries
    assert resultado.entries[0].sets
