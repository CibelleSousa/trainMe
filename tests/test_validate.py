from eval.validate import validar_exemplo

SLUGS = {"supino_reto_barra", "triceps_corda"}


def exemplo_base(**overrides):
    base = {
        "id": "x001",
        "text": "supino 3x10 com 80",
        "source": "real",
        "expected": {
            "entries": [
                {
                    "exercise": "supino_reto_barra",
                    "sets": [{"weight_kg": 80, "reps": 10, "flag": None}],
                }
            ],
            "needs_confirmation": False,
        },
    }
    base.update(overrides)
    return base


def test_exemplo_valido_sem_erros():
    assert validar_exemplo(exemplo_base(), SLUGS) == []


def test_source_invalido_gera_erro():
    erros = validar_exemplo(exemplo_base(source="chute"), SLUGS)
    assert any("source inválido" in e for e in erros)


def test_slug_desconhecido_gera_erro():
    exemplo = exemplo_base()
    exemplo["expected"]["entries"][0]["exercise"] = "nao_existe"
    erros = validar_exemplo(exemplo, SLUGS)
    assert any("slug desconhecido" in e for e in erros)


def test_exercicio_none_sem_needs_confirmation_gera_erro():
    exemplo = exemplo_base()
    exemplo["expected"]["entries"][0]["exercise"] = None
    erros = validar_exemplo(exemplo, SLUGS)
    assert any("needs_confirmation" in e for e in erros)


def test_serie_invalida_gera_erro():
    exemplo = exemplo_base()
    exemplo["expected"]["entries"][0]["sets"][0]["flag"] = "flag_invalida"
    erros = validar_exemplo(exemplo, SLUGS)
    assert any("série inválida" in e for e in erros)
