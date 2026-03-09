"""
Testes para o módulo de leads.
Cobre: criação, duplicata, validações, score, get, update status, parcial.
"""
import pytest
from httpx import AsyncClient

BASE = "/api/v1"

LEAD_VALIDO = {
    "tipo_negocio": "B2B",
    "segmento": "Tecnologia",
    "empresa": "Acme Ltda",
    "porte": "ME",
    "colaboradores": "11-50",
    "cidade": "São Paulo",
    "estado": "SP",
    "nome_contato": "João Silva",
    "email": "joao@acme.com.br",
    "whatsapp": "11999999999",
    "cargo": "Diretor de Operações",
    "usa_monday": "avaliando",
    "areas_interesse": ["Vendas", "Projetos"],
    "dor_principal": "Processos manuais em planilha",
}


# ── POST /leads ───────────────────────────────────────────────────────────────

class TestCriarLead:
    async def test_cria_lead_sucesso(self, client: AsyncClient):
        resp = await client.post(f"{BASE}/leads", json=LEAD_VALIDO)
        assert resp.status_code == 201
        data = resp.json()
        assert data["empresa"] == "Acme Ltda"
        assert data["nome_contato"] == "João Silva"
        assert data["status"] == "novo"
        assert "id" in data
        assert "created_at" in data

    async def test_email_duplicado_retorna_409(self, client: AsyncClient):
        await client.post(f"{BASE}/leads", json=LEAD_VALIDO)
        resp = await client.post(f"{BASE}/leads", json=LEAD_VALIDO)
        assert resp.status_code == 409
        detail = resp.json()["detail"]
        assert detail["code"] == "LEAD_EXISTS"
        assert "lead_id" in detail

    async def test_tipo_negocio_invalido(self, client: AsyncClient):
        payload = {**LEAD_VALIDO, "tipo_negocio": "B3C", "email": "a@test.com"}
        resp = await client.post(f"{BASE}/leads", json=payload)
        assert resp.status_code == 422

    async def test_porte_invalido(self, client: AsyncClient):
        payload = {**LEAD_VALIDO, "porte": "NANO", "email": "b@test.com"}
        resp = await client.post(f"{BASE}/leads", json=payload)
        assert resp.status_code == 422

    async def test_colaboradores_invalido(self, client: AsyncClient):
        payload = {**LEAD_VALIDO, "colaboradores": "200-300", "email": "c@test.com"}
        resp = await client.post(f"{BASE}/leads", json=payload)
        assert resp.status_code == 422

    async def test_usa_monday_invalido(self, client: AsyncClient):
        payload = {**LEAD_VALIDO, "usa_monday": "talvez", "email": "d@test.com"}
        resp = await client.post(f"{BASE}/leads", json=payload)
        assert resp.status_code == 422

    async def test_area_invalida(self, client: AsyncClient):
        payload = {**LEAD_VALIDO, "areas_interesse": ["AreaFalsa"], "email": "e@test.com"}
        resp = await client.post(f"{BASE}/leads", json=payload)
        assert resp.status_code == 422

    async def test_areas_vazia(self, client: AsyncClient):
        payload = {**LEAD_VALIDO, "areas_interesse": [], "email": "f@test.com"}
        resp = await client.post(f"{BASE}/leads", json=payload)
        assert resp.status_code == 422

    async def test_email_formato_invalido(self, client: AsyncClient):
        payload = {**LEAD_VALIDO, "email": "nao-e-um-email"}
        resp = await client.post(f"{BASE}/leads", json=payload)
        assert resp.status_code == 422

    async def test_campos_obrigatorios_ausentes(self, client: AsyncClient):
        resp = await client.post(f"{BASE}/leads", json={"email": "x@x.com"})
        assert resp.status_code == 422

    async def test_todos_os_portes_validos(self, client: AsyncClient):
        portes = ["MEI", "ME", "EPP", "Medio", "Grande"]
        for i, porte in enumerate(portes):
            payload = {**LEAD_VALIDO, "porte": porte, "email": f"porte{i}@test.com"}
            resp = await client.post(f"{BASE}/leads", json=payload)
            assert resp.status_code == 201, f"Falhou para porte={porte}: {resp.text}"

    async def test_todas_as_areas_validas(self, client: AsyncClient):
        areas = ["Vendas", "Projetos", "RH", "Financeiro", "Marketing", "Suporte", "Operacoes"]
        payload = {**LEAD_VALIDO, "areas_interesse": areas, "email": "todas@test.com"}
        resp = await client.post(f"{BASE}/leads", json=payload)
        assert resp.status_code == 201


# ── Score ─────────────────────────────────────────────────────────────────────

class TestScore:
    async def test_score_calculado_corretamente(self, client: AsyncClient):
        """
        B2B=20 + ME=5 + 11-50=5 + 2areas×5=10 + avaliando=5 + dor=5 = 50
        """
        resp = await client.post(f"{BASE}/leads", json=LEAD_VALIDO)
        lead_id = resp.json()["id"]
        detail = await client.get(f"{BASE}/leads/{lead_id}")
        assert detail.json()["score"] == 50

    async def test_score_b2c_menor(self, client: AsyncClient):
        payload = {**LEAD_VALIDO, "tipo_negocio": "B2C", "email": "b2c@test.com"}
        resp = await client.post(f"{BASE}/leads", json=payload)
        lead_id = resp.json()["id"]
        detail = await client.get(f"{BASE}/leads/{lead_id}")
        # B2C=10 (vs B2B=20), resto igual = 40
        assert detail.json()["score"] == 40

    async def test_score_maximo(self, client: AsyncClient):
        """Grande empresa B2B com 500+ pessoas e todas as áreas = score máximo."""
        areas = ["Vendas", "Projetos", "RH", "Financeiro", "Marketing", "Suporte", "Operacoes"]
        payload = {
            **LEAD_VALIDO,
            "tipo_negocio": "B2B",
            "porte": "Grande",
            "colaboradores": "500+",
            "usa_monday": "sim",
            "areas_interesse": areas,
            "dor_principal": "muita dor",
            "email": "max@test.com",
        }
        resp = await client.post(f"{BASE}/leads", json=payload)
        lead_id = resp.json()["id"]
        detail = await client.get(f"{BASE}/leads/{lead_id}")
        # B2B=20 + Grande=30 + 500+=20 + 7areas×5=35 + sim=10 + dor=5 = 120
        assert detail.json()["score"] == 120

    async def test_score_sem_opcional(self, client: AsyncClient):
        """Sem colaboradores, usa_monday e dor_principal."""
        payload = {
            "tipo_negocio": "B2B",
            "segmento": "Tech",
            "empresa": "Min Ltda",
            "porte": "MEI",
            "nome_contato": "Ana",
            "email": "min@test.com",
            "areas_interesse": ["Vendas"],
        }
        resp = await client.post(f"{BASE}/leads", json=payload)
        lead_id = resp.json()["id"]
        detail = await client.get(f"{BASE}/leads/{lead_id}")
        # B2B=20 + MEI=2 + 1area×5=5 = 27
        assert detail.json()["score"] == 27


# ── GET /leads/{id} ───────────────────────────────────────────────────────────

class TestBuscarLead:
    async def test_busca_lead_sucesso(self, client: AsyncClient):
        create = await client.post(f"{BASE}/leads", json=LEAD_VALIDO)
        lead_id = create.json()["id"]
        resp = await client.get(f"{BASE}/leads/{lead_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == LEAD_VALIDO["email"]
        assert data["areas_interesse"] == LEAD_VALIDO["areas_interesse"]
        assert data["segmento"] == "Tecnologia"

    async def test_lead_nao_encontrado(self, client: AsyncClient):
        resp = await client.get(f"{BASE}/leads/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404
        assert resp.json()["detail"]["code"] == "LEAD_NOT_FOUND"

    async def test_id_invalido_retorna_422(self, client: AsyncClient):
        resp = await client.get(f"{BASE}/leads/nao-e-um-uuid")
        assert resp.status_code == 422


# ── PATCH /leads/{id}/status ─────────────────────────────────────────────────

class TestAtualizarStatus:
    async def test_atualiza_status_sucesso(self, client: AsyncClient):
        create = await client.post(f"{BASE}/leads", json=LEAD_VALIDO)
        lead_id = create.json()["id"]
        resp = await client.patch(
            f"{BASE}/leads/{lead_id}/status", json={"status": "call_agendada"}
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "call_agendada"

    async def test_todos_os_status_validos(self, client: AsyncClient):
        statuses = [
            "novo", "planejamento_gerado", "call_agendada",
            "proposta_enviada", "fechado_ganho", "fechado_perdido",
        ]
        create = await client.post(f"{BASE}/leads", json=LEAD_VALIDO)
        lead_id = create.json()["id"]
        for status in statuses:
            resp = await client.patch(
                f"{BASE}/leads/{lead_id}/status", json={"status": status}
            )
            assert resp.status_code == 200, f"Falhou para status={status}"

    async def test_status_invalido(self, client: AsyncClient):
        create = await client.post(f"{BASE}/leads", json=LEAD_VALIDO)
        lead_id = create.json()["id"]
        resp = await client.patch(
            f"{BASE}/leads/{lead_id}/status", json={"status": "status_falso"}
        )
        assert resp.status_code == 422

    async def test_lead_nao_encontrado(self, client: AsyncClient):
        resp = await client.patch(
            f"{BASE}/leads/00000000-0000-0000-0000-000000000000/status",
            json={"status": "call_agendada"},
        )
        assert resp.status_code == 404


# ── POST /leads/partial ───────────────────────────────────────────────────────

class TestLeadParcial:
    async def test_salva_parcial_sucesso(self, client: AsyncClient):
        payload = {
            "step_completed": 2,
            "data": {"tipo_negocio": "B2B", "segmento": "Tech", "empresa": "X", "porte": "ME"},
        }
        resp = await client.post(f"{BASE}/leads/partial", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["step_completed"] == 2
        assert data["recoverable"] is True
        assert "id" in data

    async def test_step_invalido_menor(self, client: AsyncClient):
        resp = await client.post(f"{BASE}/leads/partial", json={"step_completed": 0, "data": {}})
        assert resp.status_code == 422

    async def test_step_invalido_maior(self, client: AsyncClient):
        resp = await client.post(f"{BASE}/leads/partial", json={"step_completed": 5, "data": {}})
        assert resp.status_code == 422

    async def test_ids_parciais_unicos(self, client: AsyncClient):
        payload = {"step_completed": 1, "data": {"tipo_negocio": "B2B"}}
        r1 = await client.post(f"{BASE}/leads/partial", json=payload)
        r2 = await client.post(f"{BASE}/leads/partial", json=payload)
        assert r1.json()["id"] != r2.json()["id"]
