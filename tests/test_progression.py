from app.progression import suggest_next


def sessao(weight_kg, reps_por_serie, com_personal=False, flags=None):
    flags = flags or [None] * len(reps_por_serie)
    sets = [
        {"weight_kg": weight_kg, "reps": r, "flag": f}
        for r, f in zip(reps_por_serie, flags)
    ]
    return {"com_personal": com_personal, "sets": sets}


def test_sobe_carga_quando_todas_series_no_topo_da_faixa():
    historico = [sessao(80, [12, 12, 12, 12])]
    r = suggest_next(historico)
    assert r["acao"] == "subir_carga"
    assert r["weight_kg"] == 82.5
    assert r["reps_alvo"] == 8


def test_mantem_carga_e_mira_mais_uma_rep_na_serie_mais_fraca():
    historico = [sessao(80, [10, 9, 10, 8])]
    r = suggest_next(historico)
    assert r["acao"] == "manter_carga"
    assert r["weight_kg"] == 80
    assert r["reps_alvo"] == 9


def test_ignora_series_de_aquecimento():
    historico = [sessao(80, [20, 12, 12, 12, 12], flags=["warmup", None, None, None, None])]
    r = suggest_next(historico)
    assert r["acao"] == "subir_carga"
    assert r["weight_kg"] == 82.5


def test_peso_corporal_sem_carga():
    historico = [sessao(None, [12, 12, 12])]
    r = suggest_next(historico)
    assert r["acao"] == "subir_carga"
    assert r["weight_kg"] is None


def test_faixa_de_repeticoes_configuravel():
    historico = [sessao(50, [6, 6, 6])]
    r = suggest_next(historico, rep_range=(4, 6))
    assert r["acao"] == "subir_carga"
    assert r["reps_alvo"] == 4


def test_passo_de_carga_customizado_por_exercicio():
    historico = [sessao(50, [12, 12, 12])]
    r = suggest_next(historico, step_kg=5)
    assert r["weight_kg"] == 55


def test_estagnado_apos_n_sessoes_sem_progresso():
    historico = [sessao(80, [9, 9, 9]) for _ in range(3)]
    r = suggest_next(historico)
    assert r["estagnado"] is True
    assert r["sessoes_sem_progresso"] == 3


def test_sessao_com_personal_nao_conta_para_estagnado():
    historico = [
        sessao(80, [9, 9, 9]),
        sessao(80, [9, 9, 9], com_personal=True),
        sessao(80, [9, 9, 9]),
    ]
    r = suggest_next(historico, stagnation_n=2)
    assert r["estagnado"] is True
    assert r["sessoes_sem_progresso"] == 2
