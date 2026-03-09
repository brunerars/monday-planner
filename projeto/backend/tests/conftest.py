"""
Fixtures de teste.

Estratégia:
- asyncio_default_fixture_loop_scope = session → único event loop para todos os testes
- Tabelas criadas uma vez por sessão (assume alembic upgrade head já rodou)
- Limpeza entre testes via DELETE (respeita FK, sem locks de TRUNCATE)
- Redis no DB=1 para isolamento
"""
from typing import AsyncGenerator
from unittest.mock import AsyncMock, patch

import pytest_asyncio
import redis.asyncio as aioredis
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.utils.redis_client as redis_module
from app.config import settings
from app.dependencies import get_db
from app.models.base import Base

# Engine compartilhado — um único loop de sessão evita conflitos de asyncpg
_engine = create_async_engine(settings.database_url, echo=False, pool_size=5)
_SessionFactory = async_sessionmaker(_engine, expire_on_commit=False)

# Ordem de deleção respeita FK (filhos antes dos pais)
_DELETE_ORDER = ["plans", "chat_messages", "chat_sessions", "leads"]


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables():
    """Recria o schema a cada sessão de testes para garantir que novos campos estejam presentes."""
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    await _engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def test_redis() -> aioredis.Redis:
    """Redis no DB=1 para não sujar o DB=0 de dev."""
    url = settings.redis_url
    test_url = url[:-2] + "/1" if url.endswith("/0") else url.rstrip("/") + "/1"
    r = aioredis.from_url(test_url, decode_responses=True)
    await r.ping()
    redis_module._redis = r
    yield r
    await r.flushdb()
    await r.aclose()
    redis_module._redis = None


@pytest_asyncio.fixture(autouse=True)
async def clean_tables(create_tables):
    """Limpa todas as linhas após cada teste."""
    yield
    async with _engine.begin() as conn:
        for table in _DELETE_ORDER:
            await conn.execute(text(f'DELETE FROM "{table}"'))


@pytest_asyncio.fixture(autouse=True)
async def clean_redis(test_redis: aioredis.Redis):
    """Flush Redis entre testes."""
    yield
    await test_redis.flushdb()


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with _SessionFactory() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session: AsyncSession, test_redis) -> AsyncGenerator[AsyncClient, None]:
    from app.main import app

    async def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db

    # Lifespan não precisa re-inicializar Redis (já setado pela fixture)
    with patch.object(redis_module, "init_redis", new=AsyncMock()):
        with patch.object(redis_module, "close_redis", new=AsyncMock()):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                yield ac

    app.dependency_overrides.clear()
