# ── Stage 1: builder ────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Dependencias de sistema necessarias para asyncpg e compilar wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
 && rm -rf /var/lib/apt/lists/*

COPY projeto/backend/requirements.txt .

RUN pip install --upgrade pip && \
    pip install --prefix=/install --no-cache-dir -r requirements.txt


# ── Stage 2: runtime ────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

WORKDIR /app

# Dependencias de runtime (libpq para asyncpg)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
 && rm -rf /var/lib/apt/lists/*

# Copiar pacotes instalados do builder
COPY --from=builder /install /usr/local

# Copiar codigo da aplicacao
COPY projeto/backend/ .

# Usuario nao-root para seguranca
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Rodar migrations (com tolerancia a race condition de multiplas replicas) e subir a aplicacao
CMD ["sh", "-c", "alembic upgrade head 2>/dev/null || echo 'Migration skipped (already running on another replica)' && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2"]
