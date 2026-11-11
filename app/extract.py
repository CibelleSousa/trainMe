import json
from pathlib import Path

from dotenv import load_dotenv
from pydantic import ValidationError

from app.exercises import compute_weight, load_exercises, normalize_exercise
from app.llm.base import LLMClient
from app.schemas import ExtractionResult

load_dotenv()

FEWSHOT_PATH = Path(__file__).resolve().parent.parent / "eval" / "data" / "fewshot.jsonl"

REGRAS = """\
Regras de leitura:
- Cada "NxM" ou "série de M" com carga C gera N séries iguais (carga C, M repetições).
- Se o número de séries não for dito, use 3.
- "Até a falha" sem "todas": marque flag "failure" só na última série do exercício.
  "Todas até a falha": marque "failure" em todas as séries de trabalho.
- Aquecimento dito: marque flag "warmup" nessa série (ela não entra na dupla progressão).
- Drop com carga dita ("drop pra 20 por 8"): acrescente uma série extra com flag "dropset".
  Drop sem carga: marque "dropset" na própria última série.
- Autocorreção ("na verdade foi 140"): use o valor final, ignore o valor substituído.
- Repetição feita com ajuda do personal não conta: use o número sem ajuda.
- Número aproximado ("uns 20 e poucos, acho que 22"): use o número dito (22).
- "Cada lado" ou "cada" em halteres: use a carga dita, não multiplique.
- Supino reto com barra: a pessoa fala só a anilha de um lado (ex.: "7,5 de sempre").
  Devolva esse valor falado em weight_kg, sem somar a barra — a normalização por código
  calcula o total depois. "Só a barra" = weight_kg 0.
- Devolva sempre exercise_raw como a pessoa falou (não normalize o nome do exercício).
- Se a mensagem não tiver nenhum dado de série, devolva entries vazio e needs_confirmation=true.
"""


def _lista_exercicios_para_prompt() -> str:
    linhas = []
    for ex in load_exercises():
        aliases = ", ".join(ex.get("aliases", []))
        linhas.append(f"- {ex['nome']} (aliases: {aliases})")
    return "\n".join(linhas)


def _fewshot_para_prompt() -> str:
    blocos = []
    with FEWSHOT_PATH.open(encoding="utf-8") as f:
        for linha in f:
            exemplo = json.loads(linha)
            blocos.append(
                f"Texto: {exemplo['text']}\nJSON: {json.dumps(exemplo['output'], ensure_ascii=False)}"
            )
    return "\n\n".join(blocos)


def montar_prompt(text: str) -> str:
    return f"""\
Você extrai dados estruturados de relatos em português sobre treino de musculação.
Devolva só o JSON no formato pedido, sem comentário.

Exercícios canônicos conhecidos:
{_lista_exercicios_para_prompt()}

{REGRAS}

Exemplos:
{_fewshot_para_prompt()}

Texto: {text}
JSON:"""


def extract(client: LLMClient, text: str) -> ExtractionResult:
    schema = ExtractionResult.model_json_schema()
    prompt = montar_prompt(text)

    for tentativa in range(2):
        bruto = client.extract(prompt, schema)
        try:
            return ExtractionResult.model_validate(bruto)
        except (ValidationError, json.JSONDecodeError, TypeError):
            if tentativa == 1:
                raise
    raise RuntimeError("inalcançável")


def normalizar_resultado(resultado: ExtractionResult) -> dict:
    entradas_normalizadas = []
    needs_confirmation = resultado.needs_confirmation
    for entrada in resultado.entries:
        slug = normalize_exercise(entrada.exercise_raw)
        if slug is None:
            needs_confirmation = True
        series = [
            {
                "weight_kg": compute_weight(slug, s.weight_kg) if slug and s.weight_kg is not None else s.weight_kg,
                "reps": s.reps,
                "flag": s.flag,
            }
            for s in entrada.sets
        ]
        entradas_normalizadas.append(
            {"exercise_raw": entrada.exercise_raw, "exercise_slug": slug, "sets": series}
        )
    return {"entries": entradas_normalizadas, "needs_confirmation": needs_confirmation}


def _criar_client(provider: str) -> LLMClient:
    if provider == "ollama":
        from app.llm.ollama_client import OllamaClient

        return OllamaClient()
    if provider == "gemini":
        from app.llm.gemini_client import GeminiClient

        return GeminiClient()
    raise ValueError(f"provider desconhecido: {provider}")


def _main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Extrai dados de treino de um texto livre")
    parser.add_argument("text")
    parser.add_argument("--provider", choices=["ollama", "gemini"], default="ollama")
    args = parser.parse_args()

    client = _criar_client(args.provider)
    resultado = extract(client, args.text)

    print("JSON extraído:")
    print(resultado.model_dump_json(indent=2))

    print("\nNormalizado:")
    print(json.dumps(normalizar_resultado(resultado), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    _main()
