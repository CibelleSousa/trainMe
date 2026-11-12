from datetime import date as date_type

from sqlmodel import Session as DbSession
from sqlmodel import select

from app.exercises import carga_modo_do_exercicio
from app.extract import criar_client, extract, normalizar_resultado
from app.llm.base import LLMClient
from app.models import ExerciseLog, Session, SetLog
from app.progression import suggest_next as progression_suggest_next

MENSAGEM_SCHEMA = {
    "type": "object",
    "properties": {"mensagem": {"type": "string"}},
    "required": ["mensagem"],
}

FAIXA_AMBIGUIDADE_LADO = (0.4, 0.6)


def log_sets(db: DbSession, data: date_type, raw_text: str, com_personal: bool, normalizado: dict) -> dict:
    sessao = Session(date=data, raw_text=raw_text, com_personal=com_personal)
    db.add(sessao)
    db.commit()
    db.refresh(sessao)

    exercicios_salvos = []
    for entrada in normalizado["entries"]:
        log = ExerciseLog(
            session_id=sessao.id,
            exercise_raw=entrada["exercise_raw"],
            exercise_slug=entrada["exercise_slug"],
            needs_confirmation=entrada["exercise_slug"] is None,
        )
        db.add(log)
        db.commit()
        db.refresh(log)

        for i, s in enumerate(entrada["sets"], start=1):
            db.add(SetLog(exercise_log_id=log.id, set_number=i, weight_kg=s["weight_kg"], reps=s["reps"], flag=s["flag"]))
        db.commit()

        exercicios_salvos.append(
            {"slug": entrada["exercise_slug"], "exercise_raw": entrada["exercise_raw"], "n_series": len(entrada["sets"])}
        )

    return {"session_id": sessao.id, "exercicios": exercicios_salvos}


def get_history(db: DbSession, exercise_slug: str, limit: int = 10) -> list[dict]:
    logs = db.exec(select(ExerciseLog).where(ExerciseLog.exercise_slug == exercise_slug)).all()

    pares = []
    for log in logs:
        sessao = db.get(Session, log.session_id)
        pares.append((sessao.date, sessao.com_personal, log))
    pares.sort(key=lambda p: p[0])
    pares = pares[-limit:]

    historico = []
    for _data, com_personal, log in pares:
        sets = db.exec(select(SetLog).where(SetLog.exercise_log_id == log.id).order_by(SetLog.set_number)).all()
        historico.append(
            {
                "com_personal": com_personal,
                "sets": [{"weight_kg": s.weight_kg, "reps": s.reps, "flag": s.flag} for s in sets],
            }
        )
    return historico


def suggest_next_tool(historico: list[dict], **kwargs) -> dict:
    if not historico:
        return {"acao": "sem_historico"}
    return progression_suggest_next(historico, **kwargs)


def _prompt_mensagem_final(tool_outputs: dict) -> str:
    import json

    return f"""\
Você é um assistente de treino. Escreva uma mensagem curta em português confirmando
o que foi salvo e, se houver, a sugestão para a próxima sessão.
Use SOMENTE os números abaixo (saída das ferramentas). Não invente nenhum número.

Dados das ferramentas:
{json.dumps(tool_outputs, ensure_ascii=False, default=str)}

Mensagem:"""


def _pergunta_confirmacao(normalizado: dict) -> str:
    desconhecidos = [e["exercise_raw"] for e in normalizado["entries"] if e["exercise_slug"] is None]
    if desconhecidos:
        itens = ", ".join(repr(d) for d in desconhecidos)
        return f"Não reconheci esse(s) exercício(s): {itens}. Qual é o nome certo?"
    return "Não encontrei dados de série nessa mensagem. Pode repetir com exercício, carga e repetições?"


def _ultima_carga_historico(historico: list[dict]) -> float | None:
    for sessao in reversed(historico):
        for s in sessao["sets"]:
            if s.get("weight_kg") is not None:
                return s["weight_kg"]
    return None


def ambiguidade_de_lado(entrada: dict, historico: list[dict]) -> bool:
    if carga_modo_do_exercicio(entrada["exercise_slug"]) == "anilhas_por_lado":
        return False
    if not entrada["sets"]:
        return False

    primeira_serie = entrada["sets"][0]
    if primeira_serie.get("por_lado"):
        return False

    carga = primeira_serie.get("weight_kg")
    ultima = _ultima_carga_historico(historico)
    if carga is None or not ultima:
        return False

    piso, topo = FAIXA_AMBIGUIDADE_LADO
    return piso <= carga / ultima <= topo


def _pergunta_lado(entrada: dict) -> str:
    carga = entrada["sets"][0]["weight_kg"]
    return f"A carga de {carga}kg em {entrada['exercise_raw']!r} é por lado (cada anilha/halter) ou o total? Pode confirmar antes de eu salvar?"


def carga_implausivel(entrada: dict, historico: list[dict]) -> bool:
    """Carga calculada muito diferente da última registrada: mais de 1,5x, ou 40-60% dela."""
    if not entrada["sets"]:
        return False

    primeira_serie = entrada["sets"][0]
    if primeira_serie.get("por_lado"):
        return False

    carga = primeira_serie.get("weight_kg")
    ultima = _ultima_carga_historico(historico)
    if carga is None or not ultima:
        return False

    razao = carga / ultima
    piso, topo = FAIXA_AMBIGUIDADE_LADO
    return razao > 1.5 or (piso <= razao <= topo)


def _motivo_erro(erro: Exception) -> str:
    # Só tipo do erro + código HTTP se tiver (ex.: 429, 503); nunca a mensagem
    # crua, que pode ecoar o texto do pedido em erro de validação da API.
    codigo = getattr(erro, "code", None)
    return f"{type(erro).__name__} {codigo}" if codigo else type(erro).__name__


class Agent:
    def __init__(
        self,
        primary: LLMClient | None = None,
        fallback: LLMClient | None = None,
        primary_name: str = "gemini",
        fallback_name: str = "ollama",
    ):
        self.primary = primary or criar_client("gemini")
        self.fallback = fallback or criar_client("ollama")
        self.primary_name = primary_name
        self.fallback_name = fallback_name
        self.ultimo_provider: str | None = None
        self.ultimo_fallback_motivo: str | None = None

    def _extrair(self, text: str):
        try:
            resultado = extract(self.primary, text)
            self.ultimo_provider = self.primary_name
            return resultado
        except Exception as erro:
            self.ultimo_fallback_motivo = _motivo_erro(erro)
            resultado = extract(self.fallback, text)
            self.ultimo_provider = self.fallback_name
            return resultado

    def _compor_mensagem(self, prompt: str) -> str:
        try:
            saida = self.primary.extract(prompt, MENSAGEM_SCHEMA)
            self.ultimo_provider = self.primary_name
        except Exception as erro:
            self.ultimo_fallback_motivo = _motivo_erro(erro)
            saida = self.fallback.extract(prompt, MENSAGEM_SCHEMA)
            self.ultimo_provider = self.fallback_name
        return saida["mensagem"]

    def handle_message(self, db: DbSession, text: str, data: date_type, com_personal: bool = False) -> str:
        self.ultimo_provider = None
        self.ultimo_fallback_motivo = None
        resultado = self._extrair(text)
        normalizado = normalizar_resultado(resultado)

        if normalizado["needs_confirmation"]:
            return _pergunta_confirmacao(normalizado)

        primeiro = next((e for e in normalizado["entries"] if e["exercise_slug"]), None)

        historico = []
        if primeiro:
            historico = get_history(db, primeiro["exercise_slug"])
            if ambiguidade_de_lado(primeiro, historico) or carga_implausivel(primeiro, historico):
                return _pergunta_lado(primeiro)

        resumo_log = log_sets(db, data, text, com_personal, normalizado)
        tool_outputs = {"log_sets": resumo_log}

        if primeiro:
            sessao_atual = {"com_personal": com_personal, "sets": primeiro["sets"]}
            historico_atualizado = historico + [sessao_atual]
            tool_outputs["get_history"] = historico_atualizado
            tool_outputs["suggest_next"] = suggest_next_tool(historico_atualizado)

        return self._compor_mensagem(_prompt_mensagem_final(tool_outputs))
