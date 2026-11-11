from eval.report import comparar_exemplo, normalizar_saida


def expected_simples():
    return {
        "entries": [
            {"exercise": "supino_reto_barra", "sets": [{"weight_kg": 35.0, "reps": 10, "flag": None}]}
        ],
        "needs_confirmation": False,
    }


def test_normalizar_saida_calcula_carga_total():
    output = {"entries": [{"exercise_raw": "supino", "sets": [{"weight_kg": 7.5, "reps": 10, "flag": None}]}]}
    normalizado = normalizar_saida(output)
    assert normalizado["entries"][0]["exercise"] == "supino_reto_barra"
    assert normalizado["entries"][0]["sets"][0]["weight_kg"] == 35.0


def test_comparar_exemplo_bate_tudo():
    output = {"entries": [{"exercise_raw": "supino", "sets": [{"weight_kg": 7.5, "reps": 10, "flag": None}]}]}
    r = comparar_exemplo(expected_simples(), output)
    assert r["json_valido"] is True
    assert r["ex_ok"] == 1 and r["ex_total"] == 1
    assert r["serie_ok"] == 1 and r["serie_total"] == 1
    assert r["exact"] is True
    assert r["erros"] == []


def test_comparar_exemplo_detecta_troca_de_exercicio():
    output = {"entries": [{"exercise_raw": "remada serrote", "sets": [{"weight_kg": 35.0, "reps": 10, "flag": None}]}]}
    r = comparar_exemplo(expected_simples(), output)
    assert r["ex_ok"] == 0
    assert any(e.startswith("TROCA DE EXERCICIO") for e in r["erros"])
    assert r["exact"] is False


def test_comparar_exemplo_detecta_carga_errada():
    output = {"entries": [{"exercise_raw": "supino", "sets": [{"weight_kg": 10.0, "reps": 10, "flag": None}]}]}
    r = comparar_exemplo(expected_simples(), output)
    assert r["serie_ok"] == 0
    assert any(e.startswith("CARGA ERRADA") for e in r["erros"])


def test_comparar_exemplo_output_none_conta_como_invalido():
    r = comparar_exemplo(expected_simples(), None)
    assert r["json_valido"] is False
    assert r["exact"] is False
