import csv
import io
import time
from contextlib import asynccontextmanager
from datetime import date as date_type
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlmodel import func, select

from app.agent import Agent, get_history, suggest_next_tool
from app.db import create_db_and_tables, get_session
from app.models import ExerciseLog, Session, SetLog

STATIC_DIR = Path(__file__).resolve().parent / "static"
APP_DIR = STATIC_DIR / "app"


@asynccontextmanager
async def _lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(lifespan=_lifespan)
_agent = Agent()

if (APP_DIR / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=APP_DIR / "assets"), name="assets")


class ChatRequest(BaseModel):
    text: str
    date: date_type | None = None
    com_personal: bool = False


class LoggedSet(BaseModel):
    exercise: str
    weight_kg: float | None
    reps: int


class Suggestion(BaseModel):
    acao: str
    weight_kg: float | None = None
    reps_alvo: int | None = None
    estagnado: bool = False
    sessoes_sem_progresso: int = 0


class ChatResponse(BaseModel):
    reply: str
    logged: list[LoggedSet] = []
    suggestion: Suggestion | None = None


@app.get("/")
def pagina_inicial() -> FileResponse:
    pagina_nova = APP_DIR / "index.html"
    if pagina_nova.exists():
        return FileResponse(pagina_nova)
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/simple")
def pagina_simples() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    inicio = time.monotonic()
    with get_session() as db:
        sessao_antes = db.exec(select(func.max(Session.id))).one()
        resposta = _agent.handle_message(db, req.text, req.date or date_type.today(), req.com_personal)
        sessao_depois = db.exec(select(func.max(Session.id))).one()

        registrados: list[LoggedSet] = []
        sugestao: Suggestion | None = None
        if sessao_depois is not None and sessao_depois != sessao_antes:
            logs = db.exec(select(ExerciseLog).where(ExerciseLog.session_id == sessao_depois)).all()
            for log in logs:
                sets = db.exec(select(SetLog).where(SetLog.exercise_log_id == log.id).order_by(SetLog.set_number)).all()
                for s in sets:
                    registrados.append(LoggedSet(exercise=log.exercise_slug or log.exercise_raw, weight_kg=s.weight_kg, reps=s.reps))

            slug_primario = next((log.exercise_slug for log in logs if log.exercise_slug), None)
            if slug_primario:
                historico = get_history(db, slug_primario)
                resultado = suggest_next_tool(historico)
                if resultado.get("acao") != "sem_historico":
                    sugestao = Suggestion(**resultado)

    duracao_s = time.monotonic() - inicio
    provider = getattr(_agent, "ultimo_provider", None)
    fallback_motivo = getattr(_agent, "ultimo_fallback_motivo", None)
    motivo = f" motivo={fallback_motivo}" if fallback_motivo else ""
    print(f"[/chat] provider={provider} fallback={fallback_motivo is not None}{motivo} duracao={duracao_s:.2f}s", flush=True)

    return ChatResponse(reply=resposta, logged=registrados, suggestion=sugestao)


@app.get("/history/{exercise}")
def history(exercise: str) -> list[dict]:
    with get_session() as db:
        logs = db.exec(select(ExerciseLog).where(ExerciseLog.exercise_slug == exercise)).all()
        resultado = []
        for log in logs:
            sessao = db.get(Session, log.session_id)
            sets = db.exec(select(SetLog).where(SetLog.exercise_log_id == log.id).order_by(SetLog.set_number)).all()
            resultado.append(
                {
                    "date": str(sessao.date),
                    "com_personal": sessao.com_personal,
                    "sets": [{"weight_kg": s.weight_kg, "reps": s.reps, "flag": s.flag} for s in sets],
                }
            )
        resultado.sort(key=lambda r: r["date"])
        return resultado


@app.get("/export.csv")
def export_csv() -> StreamingResponse:
    buffer = io.StringIO()
    escritor = csv.writer(buffer)
    escritor.writerow(["date", "exercise_slug", "exercise_raw", "set_number", "weight_kg", "reps", "flag", "com_personal"])

    with get_session() as db:
        logs = db.exec(select(ExerciseLog)).all()
        for log in logs:
            sessao = db.get(Session, log.session_id)
            sets = db.exec(select(SetLog).where(SetLog.exercise_log_id == log.id).order_by(SetLog.set_number)).all()
            for s in sets:
                escritor.writerow(
                    [sessao.date, log.exercise_slug or "", log.exercise_raw, s.set_number, s.weight_kg, s.reps, s.flag or "", sessao.com_personal]
                )

    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=historico.csv"},
    )
