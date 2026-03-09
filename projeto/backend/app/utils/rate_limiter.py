from app.utils.redis_client import get_redis
from app.config import settings


async def check_session_rate_limit(session_id: str) -> tuple[bool, int]:
    """
    Retorna (permitido, segundos_para_retry).
    Limite: RATE_LIMIT_PER_SESSION msgs por RATE_LIMIT_PER_SESSION_WINDOW_SECONDS.
    """
    redis = get_redis()
    key = f"chat:ratelimit:{session_id}"
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, settings.rate_limit_per_session_window_seconds)
    if count > settings.rate_limit_per_session:
        ttl = await redis.ttl(key)
        return False, max(ttl, 1)
    return True, 0


async def check_global_rate_limit() -> tuple[bool, int]:
    """Limite global: RATE_LIMIT_GLOBAL msgs por janela."""
    redis = get_redis()
    key = "chat:ratelimit:global"
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, settings.rate_limit_global_window_seconds)
    if count > settings.rate_limit_global:
        ttl = await redis.ttl(key)
        return False, max(ttl, 1)
    return True, 0
