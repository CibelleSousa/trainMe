def _series_de_trabalho(sessao: dict) -> list[dict]:
    return [s for s in sessao["sets"] if s.get("flag") != "warmup"]


def _peso_sessao(sessao: dict) -> float | None:
    return _series_de_trabalho(sessao)[0]["weight_kg"]


def _rep_mais_fraca(sessao: dict) -> int:
    return min(s["reps"] for s in _series_de_trabalho(sessao))


def _sessoes_sem_progresso(historico_contado: list[dict]) -> int:
    if not historico_contado:
        return 0
    contagem = 1
    atual = historico_contado[-1]
    for anterior in reversed(historico_contado[:-1]):
        if _peso_sessao(anterior) == _peso_sessao(atual) and _rep_mais_fraca(anterior) == _rep_mais_fraca(atual):
            contagem += 1
            atual = anterior
        else:
            break
    return contagem


def suggest_next(
    historico: list[dict],
    rep_range: tuple[int, int] = (8, 12),
    step_kg: float = 2.5,
    stagnation_n: int = 3,
) -> dict:
    ultima = historico[-1]
    series = _series_de_trabalho(ultima)
    piso, topo = rep_range
    peso_atual = _peso_sessao(ultima)
    todas_no_topo = all(s["reps"] >= topo for s in series)

    if todas_no_topo:
        acao = "subir_carga"
        novo_peso = peso_atual + step_kg if peso_atual is not None else None
        reps_alvo = piso
    else:
        acao = "manter_carga"
        novo_peso = peso_atual
        reps_alvo = _rep_mais_fraca(ultima) + 1

    contados = [s for s in historico if not s.get("com_personal")]
    sem_progresso = _sessoes_sem_progresso(contados)

    return {
        "acao": acao,
        "weight_kg": novo_peso,
        "reps_alvo": reps_alvo,
        "estagnado": sem_progresso >= stagnation_n,
        "sessoes_sem_progresso": sem_progresso,
    }
