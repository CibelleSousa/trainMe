from app.exercises import compute_weight, load_exercises, normalize_exercise


def test_normalize_exercise_por_alias():
    assert normalize_exercise("supino") == "supino_reto_barra"


def test_normalize_exercise_case_e_acento_insensivel():
    assert normalize_exercise("Supino Reto Barra") == "supino_reto_barra"
    assert normalize_exercise("TRÍCEPS CORDA") == "triceps_corda"


def test_normalize_exercise_desconhecido_retorna_none():
    assert normalize_exercise("exercicio que nao existe em lugar nenhum") is None


def test_abdutora_nunca_vira_adutora():
    assert normalize_exercise("abdutora") == "cadeira_abdutora"
    assert normalize_exercise("abdutoraa") == "cadeira_abdutora"


def test_adutora_nunca_vira_abdutora():
    assert normalize_exercise("adutora") == "cadeira_adutora"


def test_extensora_nao_confunde_com_mesa_flexora():
    assert normalize_exercise("extensora") == "cadeira_extensora"
    assert normalize_exercise("extensoraa") == "cadeira_extensora"
    assert normalize_exercise("flexora") == "mesa_flexora"


def test_fuzzy_ambiguo_retorna_none():
    assert normalize_exercise("xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx") is None


def test_abreviacao_maq_expande_para_maquina():
    assert normalize_exercise("maquina de triceps") == "triceps_maquina"
    assert normalize_exercise("peito maq") is None  # não existe "peito máquina" na lista


def test_abreviacao_elev_expande_para_elevacao():
    assert normalize_exercise("elev lateral") == "elevacao_lateral_halteres"


def test_abreviacao_desenv_expande_para_desenvolvimento():
    assert normalize_exercise("desenv maquina") == "desenvolvimento_maquina"


def test_abreviacao_incl_expande_para_inclinado():
    assert normalize_exercise("supino incl maquina") == "supino_inclinado_maquina"


def test_abreviacao_crucif_expande_para_crucifixo():
    assert normalize_exercise("crucif maquina") == "crucifixo_maquina"


def test_abreviacao_uni_expande_para_unilateral():
    assert normalize_exercise("triceps uni polia") == "triceps_unilateral_polia"


def test_abreviacao_nao_reabre_confusao_adutora_abdutora():
    assert normalize_exercise("cadeira abdutora") == "cadeira_abdutora"
    assert normalize_exercise("cadeira adutora") == "cadeira_adutora"


def test_ignora_preposicoes():
    assert normalize_exercise("pull down da polia") == "pull_down_polia"
    assert normalize_exercise("elevacao lateral na polia") == "elevacao_lateral_polia"
    assert normalize_exercise("puxada alta da polia") == "puxada_alta_polia"


def test_preposicao_nao_reabre_confusao_adutora_abdutora():
    assert normalize_exercise("cadeira da abdutora") == "cadeira_abdutora"
    assert normalize_exercise("cadeira da adutora") == "cadeira_adutora"


def test_singular_plural_halter_halteres():
    assert normalize_exercise("inclinado halteres") == "supino_inclinado_halteres"
    assert normalize_exercise("elevacao lateral com halter") == "elevacao_lateral_halteres"


def test_singular_plural_geral_nao_confunde_exercicios_diferentes():
    assert normalize_exercise("abdutora") == "cadeira_abdutora"
    assert normalize_exercise("adutora") == "cadeira_adutora"
    assert normalize_exercise("extensora") == "cadeira_extensora"
    assert normalize_exercise("flexora") == "mesa_flexora"


def test_todo_alias_e_nome_resolve_para_o_proprio_slug():
    # "pulldown" está em pull_down_polia E puxada_alta_polia no exercises.json:
    # ambiguidade do dado em si, não da normalização. Ignorado aqui de propósito.
    aliases_duplicados = {"pulldown"}
    for ex in load_exercises():
        for texto in [ex["nome"], *ex.get("aliases", [])]:
            if texto.strip().lower() in aliases_duplicados:
                continue
            assert normalize_exercise(texto) == ex["slug"], f"{texto!r} não resolveu para {ex['slug']}"


def test_compute_weight_anilhas_por_lado():
    assert compute_weight("supino_reto_barra", 7.5) == 35.0


def test_compute_weight_so_a_barra():
    assert compute_weight("supino_reto_barra", 0) == 20.0


def test_compute_weight_passthrough_sem_modo_especial():
    assert compute_weight("triceps_corda", 25) == 25.0
