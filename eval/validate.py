"""Valida eval/data/dataset.jsonl: schema, slugs, source, ids únicos e contaminação com fewshot."""

import json
import sys
from pathlib import Path

from pydantic import ValidationError

from app.exercises import load_exercises
from app.schemas import SetEntry

DATASET_PATH = Path(__file__).resolve().parent / "data" / "dataset.jsonl"
FEWSHOT_PATH = Path(__file__).resolve().parent / "data" / "fewshot.jsonl"
FONTES_VALIDAS = {"real", "reconstruido", "sintetico"}


def _ler_jsonl(caminho: Path) -> list[dict]:
    with caminho.open(encoding="utf-8") as f:
        return [json.loads(linha) for linha in f if linha.strip()]


def _slugs_validos() -> set[str]:
    return {ex["slug"] for ex in load_exercises()}


def validar_exemplo(exemplo: dict, slugs_validos: set[str]) -> list[str]:
    erros = []
    exemplo_id = exemplo.get("id", "<sem id>")

    if not exemplo.get("text"):
        erros.append(f"{exemplo_id}: text vazio ou ausente")

    if exemplo.get("source") not in FONTES_VALIDAS:
        erros.append(f"{exemplo_id}: source inválido: {exemplo.get('source')!r}")

    expected = exemplo.get("expected")
    if expected is None:
        erros.append(f"{exemplo_id}: expected ausente")
        return erros

    for entrada in expected.get("entries", []):
        exercise = entrada.get("exercise")
        if exercise is not None and exercise not in slugs_validos:
            erros.append(f"{exemplo_id}: slug desconhecido em expected: {exercise!r}")
        if exercise is None and not expected.get("needs_confirmation"):
            erros.append(f"{exemplo_id}: exercise None exige needs_confirmation=true")
        for s in entrada.get("sets", []):
            try:
                SetEntry.model_validate(s)
            except ValidationError as e:
                erros.append(f"{exemplo_id}: série inválida {s}: {e}")

    return erros


def validar_dataset() -> list[str]:
    erros: list[str] = []
    exemplos = _ler_jsonl(DATASET_PATH)
    slugs_validos = _slugs_validos()

    ids_vistos: dict[str, int] = {}
    for exemplo in exemplos:
        exemplo_id = exemplo.get("id")
        ids_vistos[exemplo_id] = ids_vistos.get(exemplo_id, 0) + 1
        erros.extend(validar_exemplo(exemplo, slugs_validos))

    for exemplo_id, contagem in ids_vistos.items():
        if contagem > 1:
            erros.append(f"id duplicado: {exemplo_id} aparece {contagem} vezes")

    textos_fewshot = {e["text"] for e in _ler_jsonl(FEWSHOT_PATH)}
    for exemplo in exemplos:
        if exemplo.get("text") in textos_fewshot:
            erros.append(f"{exemplo['id']}: texto igual a um exemplo do fewshot.jsonl (contaminação)")

    return erros


def main() -> None:
    erros = validar_dataset()
    if erros:
        print(f"{len(erros)} erro(s) encontrado(s):")
        for erro in erros:
            print(f"- {erro}")
        sys.exit(1)
    print("Dataset válido.")


if __name__ == "__main__":
    main()
