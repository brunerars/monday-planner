from contextlib import asynccontextmanager

import logging

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import engine
from app.utils.redis_client import init_redis, close_redis

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer() if settings.environment == "development"
        else structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(
        getattr(logging, settings.log_level.upper(), logging.INFO)
    ),
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("startup", environment=settings.environment)
    await init_redis()
    logger.info("redis_connected")
    yield
    await close_redis()
    await engine.dispose()
    logger.info("shutdown_complete")


app = FastAPI(
    title="MondayPlanner API",
    description="Plataforma de captação e planejamento inteligente para Monday.com",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled_error", path=str(request.url), error=str(exc))
    return JSONResponse(
        status_code=500,
        content={"detail": {"code": "INTERNAL_ERROR", "message": "Erro interno do servidor"}},
    )


from app.routers import leads, chat, plans, webhooks  # noqa: E402

app.include_router(leads.router, prefix="/api/v1", tags=["leads"])
app.include_router(chat.router, prefix="/api/v1", tags=["chat"])
app.include_router(plans.router, prefix="/api/v1", tags=["plans"])
app.include_router(webhooks.router, prefix="/api/v1", tags=["webhooks"])


@app.get("/health", tags=["health"], summary="Health check")
async def health_check():
    """Verifica conectividade com DB e Redis."""
    from sqlalchemy import text
    from app.utils.redis_client import get_redis

    db_status = "connected"
    redis_status = "connected"

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    try:
        await get_redis().ping()
    except Exception:
        redis_status = "error"

    overall = "healthy" if db_status == "connected" and redis_status == "connected" else "degraded"

    return {
        "status": overall,
        "version": "1.0.0",
        "services": {
            "database": db_status,
            "redis": redis_status,
            "claude_api": "not_checked",
            "monday_api": "not_checked",
        },
    }
