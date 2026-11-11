import eval.report as report_mod
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


def test_relatorio_mostra_exato_com_e_sem_ambiguo(monkeypatch):
    avals = [
        {"id": "a", "source": "real", "tags": ["ambiguo"], "latency_s": 1.0, "exact": False, "ex_ok": 0, "ex_total": 1, "serie_ok": 0, "serie_total": 1, "json_valido": True, "erros": [], "output": None},
        {"id": "b", "source": "real", "tags": [], "latency_s": 1.0, "exact": True, "ex_ok": 1, "ex_total": 1, "serie_ok": 1, "serie_total": 1, "json_valido": True, "erros": [], "output": None},
    ]
    monkeypatch.setattr(report_mod, "avaliar_config", lambda nome, dataset: avals)
    monkeypatch.setattr(report_mod, "_ler_jsonl", lambda caminho: [])

    relatorio = report_mod.gerar_relatorio(["X"])
    assert "exato_sem_ambiguo" in relatorio
    assert "1/2 (50%)" in relatorio
    assert "2/2 (100%)" in relatorio


def test_tags_com_n_pequeno_agrupam_em_outras(monkeypatch):
    def aval(id_, tags):
        return {
            "id": id_, "source": "real", "tags": tags, "latency_s": 1.0, "exact": True,
            "ex_ok": 1, "ex_total": 1, "serie_ok": 1, "serie_total": 1, "json_valido": True,
            "erros": [], "output": None,
        }

    avals = (
        [aval(f"grande{i}", ["tag_grande"]) for i in range(5)]
        + [aval("p1", ["tag_rara_a"])]
        + [aval("p2", ["tag_rara_b"])]
    )
    monkeypatch.setattr(report_mod, "avaliar_config", lambda nome, dataset: avals)
    monkeypatch.setattr(report_mod, "_ler_jsonl", lambda caminho: [])

    relatorio = report_mod.gerar_relatorio(["X"])
    assert "tag_grande" in relatorio
    assert "outras (n pequeno)" in relatorio
    assert "tag_rara_a" not in relatorio
    assert "tag_rara_b" not in relatorio
