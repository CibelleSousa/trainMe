import pytest

from app.extract import extract, normalizar_resultado


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


def test_normalizar_resultado_calcula_carga_total_anilhas_por_lado():
    client = ClientFalso(
        [
            {
                "entries": [
                    {"exercise_raw": "supino", "sets": [{"weight_kg": 7.5, "reps": 10, "flag": None}]}
                ],
                "needs_confirmation": False,
            }
        ]
    )
    resultado = extract(client, "supino com 7,5 de sempre, 10 reps")
    normalizado = normalizar_resultado(resultado)
    assert normalizado["entries"][0]["exercise_slug"] == "supino_reto_barra"
    assert normalizado["entries"][0]["sets"][0]["weight_kg"] == 35.0


def test_normalizar_resultado_exercicio_desconhecido_marca_confirmacao():
    client = ClientFalso(
        [
            {
                "entries": [
                    {"exercise_raw": "aparelho que não existe", "sets": [{"weight_kg": 10, "reps": 10, "flag": None}]}
                ],
                "needs_confirmation": False,
            }
        ]
    )
    resultado = extract(client, "fiz um negócio novo com 10, 10 reps")
    normalizado = normalizar_resultado(resultado)
    assert normalizado["entries"][0]["exercise_slug"] is None
    assert normalizado["needs_confirmation"] is True
