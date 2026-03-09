"""
Testes para o módulo de chat.
Usa mocks na Claude API para não depender de API key real.
"""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

BASE = "/api/v1"

LEAD_VALIDO = {
    "tipo_negocio": "B2B",
    "segmento": "Tecnologia",
    "empresa": "TestCorp Ltda",
    "porte": "ME",
    "colaboradores": "11-50",
    "cidade": "São Paulo",
    "estado": "SP",
    "nome_contato": "Ana Teste",
    "email": "ana@testcorp.com",
    "whatsapp": "11988888888",
    "cargo": "CEO",
    "usa_monday": "avaliando",
    "areas_interesse": ["Vendas", "Projetos"],
    "dor_principal": "Tudo em planilha",
}

MOCK_GREETING = "Olá! Fico feliz em ajudar a TestCorp com a implementação do Monday.com. Vi que a principal dor é tudo em planilha. Como funciona o processo de vendas hoje?"

MOCK_RESPONSE = "Entendi. Quantas oportunidades vocês têm por mês no pipeline de vendas?"


def _mock_claude_message(text: str):
    """Cria um mock do retorno da Claude API."""
    content_block = MagicMock()
    content_block.text = text
    response = MagicMock()
    response.content = [content_block]
    return response


async def _create_lead(client: AsyncClient) -> str:
    """Helper: cria lead e retorna ID."""
    resp = await client.post(f"{BASE}/leads", json=LEAD_VALIDO)
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


# ── POST /chat/start ──────────────────────────────────────────────────────


class TestChatStart:
    async def test_start_sucesso(self, client: AsyncClient):
        lead_id = await _create_lead(client)

        with patch(
            "app.services.agent_service._call_claude_with_retry",
            new=AsyncMock(return_value=MOCK_GREETING),
        ):
            resp = await client.post(f"{BASE}/chat/start", json={"lead_id": lead_id})

        assert resp.status_code == 201
        data = resp.json()
        assert "session_id" in data
        assert data["lead_empresa"] == "TestCorp Ltda"
        assert data["greeting"] == MOCK_GREETING
        assert data["config"]["max_messages"] == 15
        assert data["config"]["supports_audio"] is False

    async def test_lead_nao_encontrado(self, client: AsyncClient):
        resp = await client.post(
            f"{BASE}/chat/start",
            json={"lead_id": "00000000-0000-0000-0000-000000000000"},
        )
        assert resp.status_code == 404
        assert resp.json()["detail"]["code"] == "LEAD_NOT_FOUND"

    async def test_sessao_duplicada_retorna_409(self, client: AsyncClient):
        lead_id = await _create_lead(client)

        with patch(
            "app.services.agent_service._call_claude_with_retry",
            new=AsyncMock(return_value=MOCK_GREETING),
        ):
            r1 = await client.post(f"{BASE}/chat/start", json={"lead_id": lead_id})
            assert r1.status_code == 201

            r2 = await client.post(f"{BASE}/chat/start", json={"lead_id": lead_id})

        assert r2.status_code == 409
        assert r2.json()["detail"]["code"] == "SESSION_ACTIVE"
        assert "session_id" in r2.json()["detail"]


# ── POST /chat/message ────────────────────────────────────────────────────


class TestChatMessage:
    async def _start_session(self, client: AsyncClient) -> tuple[str, str]:
        """Helper: cria lead + sessão, retorna (lead_id, session_id)."""
        lead_id = await _create_lead(client)
        with patch(
            "app.services.agent_service._call_claude_with_retry",
            new=AsyncMock(return_value=MOCK_GREETING),
        ):
            resp = await client.post(f"{BASE}/chat/start", json={"lead_id": lead_id})
        return lead_id, resp.json()["session_id"]

    async def test_mensagem_sucesso(self, client: AsyncClient):
        _, session_id = await self._start_session(client)

        with patch(
            "app.services.agent_service._call_claude_with_retry",
            new=AsyncMock(return_value=MOCK_RESPONSE),
        ):
            resp = await client.post(
                f"{BASE}/chat/message",
                json={"session_id": session_id, "content": "Usamos planilhas hoje."},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["response"] == MOCK_RESPONSE
        assert "message_id" in data
        assert data["session_status"]["messages_used"] == 3  # greeting + user + assistant
        assert data["session_status"]["is_final"] is False
        assert data["plan_trigger"] is None

    async def test_sessao_inexistente(self, client: AsyncClient):
        resp = await client.post(
            f"{BASE}/chat/message",
            json={
                "session_id": "00000000-0000-0000-0000-000000000000",
                "content": "Olá",
            },
        )
        assert resp.status_code == 404

    async def test_mensagem_vazia_retorna_422(self, client: AsyncClient):
        _, session_id = await self._start_session(client)
        resp = await client.post(
            f"{BASE}/chat/message",
            json={"session_id": session_id, "content": ""},
        )
        assert resp.status_code == 422

    async def test_is_final_na_ultima_mensagem(self, client: AsyncClient):
        """Verifica que is_final=True quando session atinge o limite."""
        _, session_id = await self._start_session(client)

        # Sessão começa com 1 msg (greeting). Precisamos chegar em total_messages=15.
        # Cada chamada a /chat/message adiciona 2 (user + assistant).
        # Começa em 1, então precisamos de 7 trocas para chegar em 15.
        # Rate limiter é bypassed para não interferir no teste de fluxo.
        with patch(
            "app.services.agent_service.check_session_rate_limit",
            new=AsyncMock(return_value=(True, 0)),
        ):
            for i in range(6):
                with patch(
                    "app.services.agent_service._call_claude_with_retry",
                    new=AsyncMock(return_value=f"Resposta {i}"),
                ):
                    r = await client.post(
                        f"{BASE}/chat/message",
                        json={"session_id": session_id, "content": f"Mensagem {i}"},
                    )
                assert r.status_code == 200
                assert r.json()["session_status"]["is_final"] is False

            # 7ª troca deve ser a final (1 + 7*2 = 15)
            with patch(
                "app.services.agent_service._call_claude_with_retry",
                new=AsyncMock(return_value="Encerrando..."),
            ), patch(
                "app.services.plan_service.generate_plan_background",
                new=AsyncMock(),
            ):
                final_resp = await client.post(
                    f"{BASE}/chat/message",
                    json={"session_id": session_id, "content": "Última mensagem"},
                )

        assert final_resp.status_code == 200
        data = final_resp.json()
        assert data["session_status"]["is_final"] is True
        assert data["session_status"]["messages_remaining"] == 0
        assert data["plan_trigger"] is not None
        assert data["plan_trigger"]["status"] == "generating"

    async def test_mensagem_apos_sessao_finalizada(self, client: AsyncClient):
        """Não deve aceitar mensagens em sessão completed."""
        _, session_id = await self._start_session(client)

        # Encerra sessão
        with patch("app.services.plan_service.generate_plan_background", new=AsyncMock()):
            await client.post(
                f"{BASE}/chat/end",
                json={"session_id": session_id, "reason": "user_requested"},
            )

        # Tenta enviar mensagem
        resp = await client.post(
            f"{BASE}/chat/message",
            json={"session_id": session_id, "content": "Oi"},
        )
        assert resp.status_code == 410
        assert resp.json()["detail"]["code"] == "SESSION_EXPIRED"


# ── POST /chat/end ────────────────────────────────────────────────────────


class TestChatEnd:
    async def test_encerrar_sessao_sucesso(self, client: AsyncClient):
        lead_id = await _create_lead(client)
        with patch(
            "app.services.agent_service._call_claude_with_retry",
            new=AsyncMock(return_value=MOCK_GREETING),
        ):
            start = await client.post(f"{BASE}/chat/start", json={"lead_id": lead_id})
        session_id = start.json()["session_id"]

        with patch("app.services.plan_service.generate_plan_background", new=AsyncMock()):
            resp = await client.post(
                f"{BASE}/chat/end",
                json={"session_id": session_id, "reason": "user_requested"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert data["plan_trigger"]["status"] == "generating"
        assert "/plans/status/" in data["plan_trigger"]["poll_url"]

    async def test_encerrar_sessao_inexistente(self, client: AsyncClient):
        with patch("app.services.plan_service.generate_plan_background", new=AsyncMock()):
            resp = await client.post(
                f"{BASE}/chat/end",
                json={
                    "session_id": "00000000-0000-0000-0000-000000000000",
                    "reason": "user_requested",
                },
            )
        assert resp.status_code == 404

    async def test_encerrar_duas_vezes_retorna_409(self, client: AsyncClient):
        lead_id = await _create_lead(client)
        with patch(
            "app.services.agent_service._call_claude_with_retry",
            new=AsyncMock(return_value=MOCK_GREETING),
        ):
            start = await client.post(f"{BASE}/chat/start", json={"lead_id": lead_id})
        session_id = start.json()["session_id"]

        with patch("app.services.plan_service.generate_plan_background", new=AsyncMock()):
            await client.post(
                f"{BASE}/chat/end",
                json={"session_id": session_id, "reason": "user_requested"},
            )
            r2 = await client.post(
                f"{BASE}/chat/end",
                json={"session_id": session_id, "reason": "user_requested"},
            )

        assert r2.status_code == 409
        assert r2.json()["detail"]["code"] == "SESSION_ALREADY_ENDED"


# ── GET /chat/history/{session_id} ────────────────────────────────────────


class TestChatHistory:
    async def test_historico_sucesso(self, client: AsyncClient):
        lead_id = await _create_lead(client)
        with patch(
            "app.services.agent_service._call_claude_with_retry",
            new=AsyncMock(return_value=MOCK_GREETING),
        ):
            start = await client.post(f"{BASE}/chat/start", json={"lead_id": lead_id})
        session_id = start.json()["session_id"]

        with patch(
            "app.services.agent_service._call_claude_with_retry",
            new=AsyncMock(return_value=MOCK_RESPONSE),
        ):
            await client.post(
                f"{BASE}/chat/message",
                json={"session_id": session_id, "content": "Olá"},
            )

        resp = await client.get(f"{BASE}/chat/history/{session_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == session_id
        assert data["total_messages"] == 3  # greeting + user + assistant
        assert len(data["messages"]) == 3
        assert data["messages"][0]["role"] == "assistant"  # greeting
        assert data["messages"][1]["role"] == "user"
        assert data["messages"][2]["role"] == "assistant"

    async def test_historico_sessao_inexistente(self, client: AsyncClient):
        resp = await client.get(
            f"{BASE}/chat/history/00000000-0000-0000-0000-000000000000"
        )
        assert resp.status_code == 404
