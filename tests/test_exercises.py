from app.exercises import compute_weight, normalize_exercise


def test_normalize_exercise_por_alias():
    assert normalize_exercise("supino") == "supino_reto_barra"


def test_normalize_exercise_case_e_acento_insensivel():
    assert normalize_exercise("Supino Reto Barra") == "supino_reto_barra"
    assert normalize_exercise("TRÍCEPS CORDA") == "triceps_corda"


def test_normalize_exercise_desconhecido_retorna_none():
    assert normalize_exercise("exercicio que nao existe em lugar nenhum") is None


def test_compute_weight_anilhas_por_lado():
    assert compute_weight("supino_reto_barra", 7.5) == 35.0


def test_compute_weight_so_a_barra():
    assert compute_weight("supino_reto_barra", 0) == 20.0


def test_compute_weight_passthrough_sem_modo_especial():
    assert compute_weight("triceps_corda", 25) == 25.0
