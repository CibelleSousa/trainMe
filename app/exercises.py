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

PREPOSICOES = {"com", "de", "da", "na", "no"}


def _normalizar_texto(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return " ".join(sem_acento.lower().replace(".", "").split())


def _singularizar(token: str) -> str:
    if len(token) > 4 and token.endswith("es"):
        return token[:-2]
    if len(token) > 3 and token.endswith("s"):
        return token[:-1]
    return token


def _chave_canonica(texto: str) -> str:
    tokens = _normalizar_texto(texto).split(" ")
    tokens = [t for t in tokens if t not in PREPOSICOES]
    tokens = [ABREVIACOES.get(t, t) for t in tokens]
    tokens = [_singularizar(t) for t in tokens]
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
            mapa[_chave_canonica(chave)] = ex["slug"]
    return mapa


def normalize_exercise(raw: str) -> str | None:
    mapa = _mapa_normalizado()
    chave = _chave_canonica(raw)
    if chave in mapa:
        return mapa[chave]

    proximos = get_close_matches(chave, mapa.keys(), n=2, cutoff=0.9)
    if len(proximos) == 1:
        return mapa[proximos[0]]
    return None


def _exercicio_por_slug(slug: str) -> dict | None:
    for ex in load_exercises():
        if ex["slug"] == slug:
            return ex
    return None


def carga_modo_do_exercicio(slug: str) -> str | None:
    ex = _exercicio_por_slug(slug)
    return ex.get("carga_modo") if ex else None


def compute_weight(slug: str, carga_falada: float, por_lado: bool = False) -> float:
    ex = _exercicio_por_slug(slug)
    if not ex:
        return float(carga_falada)

    modo = ex.get("carga_modo")
    barra_kg = ex.get("barra_kg", 0)

    if modo == "anilhas_por_lado":
        return barra_kg + 2 * carga_falada
    if modo == "por_lado_se_dito" and por_lado:
        return barra_kg + 2 * carga_falada
    return float(carga_falada)
