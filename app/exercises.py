import json
import unicodedata
from difflib import get_close_matches
from functools import lru_cache
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "exercises.json"


ABREVIACOES = {
    "maq": "maquina",
    "elev": "elevacao",
    "crucif": "crucifixo",
    "desenv": "desenvolvimento",
    "incl": "inclinado",
    "halter": "halteres",
    "uni": "unilateral",
}


def _normalizar_texto(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return " ".join(sem_acento.lower().replace(".", "").split())


def _expandir_abreviacoes(texto_normalizado: str) -> str:
    tokens = [ABREVIACOES.get(t, t) for t in texto_normalizado.split(" ")]
    return " ".join(tokens)


@lru_cache(maxsize=1)
def load_exercises() -> list[dict]:
    with DATA_PATH.open(encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _mapa_normalizado() -> dict[str, str]:
    mapa: dict[str, str] = {}
    for ex in load_exercises():
        chaves = [ex["slug"].replace("_", " "), ex["nome"], *ex.get("aliases", [])]
        for chave in chaves:
            mapa[_normalizar_texto(chave)] = ex["slug"]
    return mapa


def normalize_exercise(raw: str) -> str | None:
    mapa = _mapa_normalizado()
    chave = _normalizar_texto(raw)
    if chave in mapa:
        return mapa[chave]

    chave_expandida = _expandir_abreviacoes(chave)
    if chave_expandida in mapa:
        return mapa[chave_expandida]

    proximos = get_close_matches(chave_expandida, mapa.keys(), n=2, cutoff=0.9)
    if len(proximos) == 1:
        return mapa[proximos[0]]
    return None


def _exercicio_por_slug(slug: str) -> dict | None:
    for ex in load_exercises():
        if ex["slug"] == slug:
            return ex
    return None


def compute_weight(slug: str, carga_falada: float) -> float:
    ex = _exercicio_por_slug(slug)
    if ex and ex.get("carga_modo") == "anilhas_por_lado":
        return ex["barra_kg"] + 2 * carga_falada
    return float(carga_falada)
