"""Gera a tabela de métricas por config, por source e por tag, e lista erros reais."""

import argparse
import json
import statistics
from pathlib import Path

from app.exercises import compute_weight, normalize_exercise

ROOT = Path(__file__).resolve().parent.parent
DATASET_PATH = ROOT / "eval" / "data" / "dataset.jsonl"
RESULTS_DIR = ROOT / "results"


def _ler_jsonl(caminho: Path) -> list[dict]:
    with caminho.open(encoding="utf-8") as f:
        return [json.loads(linha) for linha in f if linha.strip()]


def normalizar_saida(output: dict) -> dict:
    entries = []
    for e in output.get("entries", []):
        slug = normalize_exercise(e["exercise_raw"])
        sets = [
            {
                "weight_kg": compute_weight(slug, s["weight_kg"]) if slug and s.get("weight_kg") is not None else s.get("weight_kg"),
                "reps": s["reps"],
                "flag": s.get("flag"),
            }
            for s in e.get("sets", [])
        ]
        entries.append({"exercise": slug, "sets": sets})
    return {"entries": entries, "needs_confirmation": output.get("needs_confirmation", False)}


def _peso_bate(esperado: float | None, obtido: float | None) -> bool:
    if esperado is None and obtido is None:
        return True
    if esperado is None or obtido is None:
        return False
    return abs(esperado - obtido) <= 0.01


def comparar_exemplo(expected: dict, output: dict | None) -> dict:
    if output is None:
        return {
            "json_valido": False,
            "ex_ok": 0,
            "ex_total": len(expected.get("entries", [])),
            "serie_ok": 0,
            "serie_total": sum(len(e["sets"]) for e in expected.get("entries", [])),
            "exact": False,
            "erros": ["chamada ao LLM falhou ou saída inválida (ver error no results)"],
        }

    obtido = normalizar_saida(output)
    entradas_exp = expected.get("entries", [])
    entradas_obt = obtido["entries"]

    ex_ok = 0
    serie_ok = 0
    serie_total = 0
    erros: list[str] = []
    exact = len(entradas_exp) == len(entradas_obt)

    for i, ent_exp in enumerate(entradas_exp):
        ent_obt = entradas_obt[i] if i < len(entradas_obt) else None
        slug_exp = ent_exp.get("exercise")
        slug_obt = ent_obt["exercise"] if ent_obt else None

        if slug_obt == slug_exp:
            ex_ok += 1
        else:
            exact = False
            erros.append(f"TROCA DE EXERCICIO: esperado {slug_exp!r}, obtido {slug_obt!r}")

        sets_exp = ent_exp.get("sets", [])
        sets_obt = ent_obt["sets"] if ent_obt else []
        for j, s_exp in enumerate(sets_exp):
            serie_total += 1
            s_obt = sets_obt[j] if j < len(sets_obt) else None
            if s_obt is None:
                exact = False
                erros.append(f"série faltando: {slug_exp} série {j + 1}")
                continue
            peso_ok = _peso_bate(s_exp.get("weight_kg"), s_obt.get("weight_kg"))
            reps_ok = s_exp.get("reps") == s_obt.get("reps")
            if peso_ok and reps_ok:
                serie_ok += 1
            else:
                exact = False
                if not peso_ok:
                    erros.append(
                        f"CARGA ERRADA: {slug_exp} série {j + 1}: esperado {s_exp.get('weight_kg')}, obtido {s_obt.get('weight_kg')}"
                    )
                if not reps_ok:
                    erros.append(
                        f"reps errada: {slug_exp} série {j + 1}: esperado {s_exp.get('reps')}, obtido {s_obt.get('reps')}"
                    )
        if len(sets_obt) > len(sets_exp):
            exact = False

    return {
        "json_valido": True,
        "ex_ok": ex_ok,
        "ex_total": len(entradas_exp),
        "serie_ok": serie_ok,
        "serie_total": serie_total,
        "exact": exact,
        "erros": erros,
    }


def _taxa(num: int, den: int) -> str:
    return f"{num / den:.0%}" if den else "n/d"


def avaliar_config(nome_config: str, dataset: list[dict]) -> list[dict]:
    resultados_path = RESULTS_DIR / f"{nome_config}.jsonl"
    if not resultados_path.exists():
        return []
    resultados = {r["id"]: r for r in _ler_jsonl(resultados_path)}

    avaliacoes = []
    for exemplo in dataset:
        resultado = resultados.get(exemplo["id"])
        if resultado is None:
            continue
        comparacao = comparar_exemplo(exemplo["expected"], resultado["output"])
        avaliacoes.append(
            {
                "id": exemplo["id"],
                "source": exemplo["source"],
                "tags": exemplo.get("tags", []),
                "text": exemplo["text"],
                "expected": exemplo["expected"],
                "output": resultado["output"],
                "latency_s": resultado["latency_s"],
                **comparacao,
            }
        )
    return avaliacoes


def _agregar(avaliacoes: list[dict]) -> dict:
    if not avaliacoes:
        return {}
    return {
        "n": len(avaliacoes),
        "json_valido": _taxa(sum(a["json_valido"] for a in avaliacoes), len(avaliacoes)),
        "exercicio": _taxa(sum(a["ex_ok"] for a in avaliacoes), sum(a["ex_total"] for a in avaliacoes)),
        "serie": _taxa(sum(a["serie_ok"] for a in avaliacoes), sum(a["serie_total"] for a in avaliacoes)),
        "exato": _taxa(sum(a["exact"] for a in avaliacoes), len(avaliacoes)),
        "latencia_mediana_s": f"{statistics.median(a['latency_s'] for a in avaliacoes):.2f}",
    }


def tabela_markdown(linhas: list[dict], colunas: list[str]) -> str:
    cabecalho = "| " + " | ".join(colunas) + " |"
    separador = "| " + " | ".join("---" for _ in colunas) + " |"
    corpo = "\n".join("| " + " | ".join(str(l.get(c, "")) for c in colunas) + " |" for l in linhas)
    return "\n".join([cabecalho, separador, corpo])


def gerar_relatorio(nomes_config: list[str]) -> str:
    dataset = _ler_jsonl(DATASET_PATH)
    partes = []

    todas_avaliacoes: dict[str, list[dict]] = {}
    for nome in nomes_config:
        todas_avaliacoes[nome] = avaliar_config(nome, dataset)

    partes.append("## Resultado por configuração\n")
    linhas = []
    for nome, avals in todas_avaliacoes.items():
        agregado = _agregar(avals)
        if agregado:
            linhas.append({"config": nome, **agregado})
    partes.append(tabela_markdown(linhas, ["config", "n", "json_valido", "exercicio", "serie", "exato", "latencia_mediana_s"]))

    partes.append("\n## Resultado por fonte (source)\n")
    for nome, avals in todas_avaliacoes.items():
        if not avals:
            continue
        partes.append(f"\n**{nome}**\n")
        fontes = sorted({a["source"] for a in avals})
        linhas = []
        for fonte in fontes:
            agregado = _agregar([a for a in avals if a["source"] == fonte])
            if agregado:
                linhas.append({"source": fonte, **agregado})
        partes.append(tabela_markdown(linhas, ["source", "n", "json_valido", "exercicio", "serie", "exato", "latencia_mediana_s"]))

    partes.append("\n## Resultado por tag\n")
    for nome, avals in todas_avaliacoes.items():
        if not avals:
            continue
        partes.append(f"\n**{nome}**\n")
        tags = sorted({t for a in avals for t in a["tags"]})
        linhas = []
        for tag in tags:
            agregado = _agregar([a for a in avals if tag in a["tags"]])
            if agregado:
                linhas.append({"tag": tag, **agregado})
        partes.append(tabela_markdown(linhas, ["tag", "n", "json_valido", "exercicio", "serie", "exato", "latencia_mediana_s"]))

    partes.append("\n## Erros reais (esperado vs obtido)\n")
    for nome, avals in todas_avaliacoes.items():
        erros_destacados = [
            (a, e) for a in avals for e in a["erros"] if e.startswith("TROCA DE EXERCICIO") or e.startswith("CARGA ERRADA")
        ]
        if not erros_destacados:
            continue
        partes.append(f"\n**{nome}** ({len(erros_destacados)} erro(s) de exercício/carga)\n")
        for a, erro in erros_destacados[:10]:
            partes.append(f"- `{a['id']}` ({a['source']}): {erro}\n  texto: \"{a['text'][:90]}...\"")

    return "\n".join(partes)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--configs", nargs="+", default=None)
    args = parser.parse_args()

    nomes = args.configs or sorted(p.stem for p in RESULTS_DIR.glob("*.jsonl"))
    relatorio = gerar_relatorio(nomes)
    print(relatorio)

    (RESULTS_DIR / "report.md").write_text(relatorio, encoding="utf-8")


if __name__ == "__main__":
    main()
