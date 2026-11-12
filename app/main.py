from contextlib import asynccontextmanager
from datetime import date as date_type

from fastapi import FastAPI
from pydantic import BaseModel

from app.agent import Agent
from app.db import create_db_and_tables, get_session


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


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    with get_session() as db:
        resposta = _agent.handle_message(db, req.text, req.date or date_type.today(), req.com_personal)
    return ChatResponse(reply=resposta)
