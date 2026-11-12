import csv
import io
from contextlib import asynccontextmanager
from datetime import date as date_type
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from sqlmodel import select

from app.agent import Agent
from app.db import create_db_and_tables, get_session
from app.models import ExerciseLog, Session, SetLog

STATIC_DIR = Path(__file__).resolve().parent / "static"


@asynccontextmanager
async def _lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(lifespan=_lifespan)
_agent = Agent()


class ChatRequest(BaseModel):
    text: str
    date: date_type | None = None
    com_personal: bool = False


class ChatResponse(BaseModel):
    reply: str


@app.get("/")
def pagina_inicial() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    with get_session() as db:
        resposta = _agent.handle_message(db, req.text, req.date or date_type.today(), req.com_personal)
    return ChatResponse(reply=resposta)


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
