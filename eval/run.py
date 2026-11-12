"""Roda uma configuração (ou todas) do eval/configs/ contra o dataset.

Salva cada resultado em results/<config>.jsonl assim que chega, e retoma
de onde parou numa próxima chamada (não refaz exemplo já salvo).
"""

import argparse
import json
import time
from pathlib import Path

import yaml

from app.extract import criar_client, extract

ROOT = Path(__file__).resolve().parent.parent
CONFIGS_DIR = ROOT / "eval" / "configs"
DATASET_PATH = ROOT / "eval" / "data" / "dataset.jsonl"
RESULTS_DIR = ROOT / "results"

PAUSA_GEMINI_S = 4.0


def _ler_jsonl(caminho: Path) -> list[dict]:
    with caminho.open(encoding="utf-8") as f:
        return [json.loads(linha) for linha in f if linha.strip()]


def carregar_config(nome: str) -> dict:
    with (CONFIGS_DIR / f"{nome}.yaml").open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def ids_ja_rodados(resultados_path: Path) -> set[str]:
    if not resultados_path.exists():
        return set()
    return {r["id"] for r in _ler_jsonl(resultados_path)}


def rodar_config(nome_config: str, limit: int | None = None, ids: set[str] | None = None) -> Path:
    config = carregar_config(nome_config)
    exemplos = _ler_jsonl(DATASET_PATH)
    if ids is not None:
        exemplos = [e for e in exemplos if e["id"] in ids]
    elif limit is not None:
        exemplos = exemplos[:limit]

    RESULTS_DIR.mkdir(exist_ok=True)
    resultados_path = RESULTS_DIR / f"{nome_config}.jsonl"

    if ids is not None and resultados_path.exists():
        # força reexecução desses ids: tira o resultado antigo deles do arquivo
        restantes = [r for r in _ler_jsonl(resultados_path) if r["id"] not in ids]
        with resultados_path.open("w", encoding="utf-8") as f:
            for r in restantes:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    feitos = ids_ja_rodados(resultados_path)

    client = criar_client(config["provider"], config.get("model"))
    few_shot = config.get("few_shot", False)

    with resultados_path.open("a", encoding="utf-8") as f:
        for exemplo in exemplos:
            if exemplo["id"] in feitos:
                continue

            inicio = time.monotonic()
            try:
                resultado = extract(client, exemplo["text"], few_shot=few_shot)
                saida = resultado.model_dump()
                erro = None
            except Exception as e:
                saida = None
                erro = f"{type(e).__name__}: {e}"
            latencia_s = time.monotonic() - inicio

            linha = {
                "id": exemplo["id"],
                "config": nome_config,
                "output": saida,
                "error": erro,
                "latency_s": latencia_s,
            }
            f.write(json.dumps(linha, ensure_ascii=False) + "\n")
            f.flush()

            if config["provider"] == "gemini":
                time.sleep(PAUSA_GEMINI_S)

    return resultados_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Roda a avaliação para uma config ou todas")
    parser.add_argument("--config", default="all")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--ids", default=None, help="ids separados por vírgula, ex.: r001,r004")
    args = parser.parse_args()

    nomes = [p.stem for p in CONFIGS_DIR.glob("*.yaml")] if args.config == "all" else [args.config]
    ids = set(args.ids.split(",")) if args.ids else None

    for nome in nomes:
        caminho = rodar_config(nome, limit=args.limit, ids=ids)
        print(f"{nome}: resultados em {caminho}")


if __name__ == "__main__":
    main()
