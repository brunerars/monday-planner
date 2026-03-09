from typing import AsyncGenerator

from fastapi import Depends, HTTPException, Header, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.utils.redis_client import get_redis
from app.config import settings
import redis.asyncio as aioredis


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


async def get_redis_dep() -> aioredis.Redis:
    return get_redis()


async def verify_internal_api_key(x_api_key: str = Header(...)) -> None:
    """Proteção para endpoints internos (webhooks)."""
    if not settings.internal_api_key:
        raise HTTPException(status_code=500, detail={"code": "CONFIG_ERROR", "message": "Internal API key não configurada"})
    if x_api_key != settings.internal_api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "API key inválida"},
        )
