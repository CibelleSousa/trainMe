# Stage 1: build a static bundle of the frontend (frontend/vite.static.config.ts),
# sem passar pelo servidor TanStack Start/Nitro — só o componente da tela renderizado
# direto, pra servir como arquivo estático pelo FastAPI.
FROM node:22-slim AS frontend-build

WORKDIR /src/frontend

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install --no-audit --no-fund

COPY frontend/ ./
RUN npx vite build --config vite.static.config.ts

# Stage 2: API Python, servindo o bundle estático
FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
COPY app ./app
COPY eval ./eval
COPY data ./data
COPY --from=frontend-build /src/app/static/app ./app/static/app

RUN pip install --no-cache-dir -e .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
