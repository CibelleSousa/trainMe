from datetime import date as date_type

from sqlmodel import Session as DbSession
from sqlmodel import select

from app.extract import criar_client, extract, normalizar_resultado
from app.llm.base import LLMClient
from app.models import ExerciseLog, Session, SetLog
from app.progression import suggest_next as progression_suggest_next

MENSAGEM_SCHEMA = {
    "type": "object",
    "properties": {"mensagem": {"type": "string"}},
    "required": ["mensagem"],
}

MAX_PASSOS = 3


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


class Agent:
    def __init__(self, primary: LLMClient | None = None, fallback: LLMClient | None = None):
        self.primary = primary or criar_client("gemini")
        self.fallback = fallback or criar_client("ollama")

    def _extrair(self, text: str):
        try:
            return extract(self.primary, text)
        except Exception:
            return extract(self.fallback, text)

    def _compor_mensagem(self, prompt: str) -> str:
        try:
            saida = self.primary.extract(prompt, MENSAGEM_SCHEMA)
        except Exception:
            saida = self.fallback.extract(prompt, MENSAGEM_SCHEMA)
        return saida["mensagem"]

    def handle_message(self, db: DbSession, text: str, data: date_type, com_personal: bool = False) -> str:
        resultado = self._extrair(text)
        normalizado = normalizar_resultado(resultado)

        if normalizado["needs_confirmation"]:
            return _pergunta_confirmacao(normalizado)

        passos = 0
        resumo_log = log_sets(db, data, text, com_personal, normalizado)
        passos += 1
        tool_outputs = {"log_sets": resumo_log}

        primeiro = next((e for e in resumo_log["exercicios"] if e["slug"]), None)
        if primeiro and passos < MAX_PASSOS:
            historico = get_history(db, primeiro["slug"])
            tool_outputs["get_history"] = historico
            passos += 1
            if passos < MAX_PASSOS:
                tool_outputs["suggest_next"] = suggest_next_tool(historico)
                passos += 1

        return self._compor_mensagem(_prompt_mensagem_final(tool_outputs))
