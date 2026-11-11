import pytest

from app.extract import extract


class ClientFalso:
    def __init__(self, respostas):
        self._respostas = list(respostas)
        self.chamadas = 0

    def extract(self, text: str, schema: dict) -> dict:
        self.chamadas += 1
        return self._respostas.pop(0)


def test_extract_valida_primeira_resposta_boa():
    client = ClientFalso(
        [
            {
                "entries": [
                    {"exercise_raw": "supino", "sets": [{"weight_kg": 80, "reps": 8, "flag": None}]}
                ],
                "needs_confirmation": False,
            }
        ]
    )
    resultado = extract(client, "supino 1x8 com 80")
    assert resultado.entries[0].exercise_raw == "supino"
    assert client.chamadas == 1


def test_extract_faz_1_retry_em_saida_invalida():
    client = ClientFalso(
        [
            {"entries": "isso não é uma lista"},
            {"entries": [], "needs_confirmation": True},
        ]
    )
    resultado = extract(client, "mensagem confusa")
    assert resultado.needs_confirmation is True
    assert client.chamadas == 2


def test_extract_propaga_erro_se_as_duas_tentativas_falharem():
    client = ClientFalso(
        [
            {"entries": "invalido"},
            {"entries": "invalido de novo"},
        ]
    )
    with pytest.raises(Exception):
        extract(client, "mensagem confusa")
    assert client.chamadas == 2
