"""
Gerenciador de contexto do agente.
Implementa sliding window (últimas 8 mensagens + summary das anteriores) com cache Redis.
"""
from typing import Optional

import structlog
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.prompts import CONTEXT_COMPRESSION_PROMPT
from app.models.chat_message import ChatMessage
from app.models.chat_session import ChatSession
from app.models.lead import Lead
from app.utils.redis_client import get_redis

logger = structlog.get_logger()

_WINDOW_SIZE = 8
_CACHE_TTL = 1800  # 30 minutos


class ContextManager:
    def _cache_key(self, session_id) -> str:
        return f"chat:session:{session_id}"

    async def build_messages(
        self,
        session: ChatSession,
        lead: Lead,
        db: AsyncSession,
    ) -> list[dict]:
        """
        Monta o array de mensagens para a Claude API.
        Sliding window: últimas WINDOW_SIZE mensagens + summary das anteriores (se houver).
        """
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session.id)
            .order_by(desc(ChatMessage.created_at))
            .limit(_WINDOW_SIZE)
        )
        recent_msgs = list(reversed(result.scalars().all()))

        messages: list[dict] = []

        # Se há mensagens além da janela, injeta o summary
        if session.total_messages > _WINDOW_SIZE:
            summary = await self._get_cached_summary(session.id)
            if not summary:
                summary = session.context_summary  # fallback para DB

            if summary:
                # Simula um par user/assistant para o summary aparecer no contexto
                messages.append({
                    "role": "user",
                    "content": f"[Resumo das mensagens anteriores desta conversa: {summary}]",
                })
                messages.append({
                    "role": "assistant",
                    "content": "Entendido. Continuo com base nesse contexto.",
                })

        for msg in recent_msgs:
            messages.append({"role": msg.role, "content": msg.content})

        return messages

    async def maybe_compress(
        self,
        session: ChatSession,
        db: AsyncSession,
        claude_client,
    ) -> None:
        """
        Comprime mensagens antigas via Claude quando ultrapassamos a janela.
        Executa apenas a cada 4 mensagens além do limite para não chamar a API toda vez.
        """
        messages_beyond = session.total_messages - _WINDOW_SIZE
        if messages_beyond <= 0:
            return

        # Comprime na primeira vez que ultrapassa a janela e depois a cada 4 mensagens
        if messages_beyond == 1 or messages_beyond % 4 == 0:
            await self._do_compress(session, db, claude_client)

    async def _do_compress(
        self,
        session: ChatSession,
        db: AsyncSession,
        claude_client,
    ) -> None:
        """Gera summary das mensagens mais antigas via Claude Haiku (barato)."""
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session.id)
            .order_by(ChatMessage.created_at)
        )
        all_msgs = result.scalars().all()
        old_msgs = all_msgs[:-_WINDOW_SIZE]

        if not old_msgs:
            return

        conv_text = "\n".join(
            f"{msg.role.upper()}: {msg.content}" for msg in old_msgs
        )

        prompt = CONTEXT_COMPRESSION_PROMPT.format(messages=conv_text)

        try:
            response = await claude_client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}],
            )
            summary = response.content[0].text

            # Salva no Redis
            await self._set_cached_summary(session.id, summary)

            # Persiste no DB como fallback
            session.context_summary = summary
            await db.commit()

            logger.info("context_compressed", session_id=str(session.id))
        except Exception as exc:
            logger.warning("context_compression_failed", error=str(exc))

    async def _get_cached_summary(self, session_id) -> Optional[str]:
        redis = get_redis()
        return await redis.hget(self._cache_key(session_id), "summary")

    async def _set_cached_summary(self, session_id, summary: str) -> None:
        redis = get_redis()
        key = self._cache_key(session_id)
        await redis.hset(key, "summary", summary)
        await redis.expire(key, _CACHE_TTL)

    async def invalidate_cache(self, session_id) -> None:
        redis = get_redis()
        await redis.delete(self._cache_key(session_id))
