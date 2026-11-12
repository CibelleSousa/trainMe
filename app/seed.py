"""Carrega data/progression_sim.csv no banco. Idempotente: roda de novo sem duplicar."""

import csv
from collections import defaultdict
from datetime import date as date_type
from pathlib import Path

from sqlmodel import select

from app.db import create_db_and_tables, get_session
from app.models import ExerciseLog, Session, SetLog

CSV_PATH = Path(__file__).resolve().parent.parent / "data" / "progression_sim.csv"


def _marcador(data_str: str) -> str:
    return f"seed:progression_sim.csv:{data_str}"


def _ler_csv() -> list[dict]:
    with CSV_PATH.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def seed() -> dict:
    por_dia: dict[str, list[dict]] = defaultdict(list)
    for linha in _ler_csv():
        por_dia[linha["date"]].append(linha)

    resumo = {"sessoes_criadas": 0, "exercicios_criados": 0, "series_criadas": 0}

    with get_session() as db:
        for data_str, linhas_do_dia in por_dia.items():
            marcador = _marcador(data_str)
            if db.exec(select(Session).where(Session.raw_text == marcador)).first():
                continue

            com_personal = linhas_do_dia[0]["com_personal"].strip().lower() == "true"
            sessao = Session(date=date_type.fromisoformat(data_str), raw_text=marcador, com_personal=com_personal)
            db.add(sessao)
            db.commit()
            db.refresh(sessao)
            resumo["sessoes_criadas"] += 1

            por_exercicio: dict[str, list[dict]] = defaultdict(list)
            for linha in linhas_do_dia:
                por_exercicio[linha["exercise"]].append(linha)

            for exercicio_slug, linhas_exercicio in por_exercicio.items():
                log = ExerciseLog(session_id=sessao.id, exercise_raw=exercicio_slug, exercise_slug=exercicio_slug)
                db.add(log)
                db.commit()
                db.refresh(log)
                resumo["exercicios_criados"] += 1

                for linha in linhas_exercicio:
                    db.add(
                        SetLog(
                            exercise_log_id=log.id,
                            set_number=int(linha["set_number"]),
                            weight_kg=float(linha["weight_kg"]) if linha["weight_kg"] else None,
                            reps=int(linha["reps"]),
                            flag=linha["flag"] or None,
                        )
                    )
                    resumo["series_criadas"] += 1
            db.commit()

    return resumo


def main() -> None:
    create_db_and_tables()
    resumo = seed()
    print(
        f"Sessões novas: {resumo['sessoes_criadas']}, "
        f"exercícios: {resumo['exercicios_criados']}, séries: {resumo['series_criadas']}"
    )


if __name__ == "__main__":
    main()
