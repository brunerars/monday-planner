"""Testes para o endpoint de health check."""


async def test_health_retorna_200(client):
    resp = await client.get("/health")
    assert resp.status_code == 200


async def test_health_estrutura(client):
    resp = await client.get("/health")
    data = resp.json()
    assert "status" in data
    assert "version" in data
    assert "services" in data
    assert data["status"] in ("healthy", "degraded")


async def test_health_servicos_presentes(client):
    data = (await client.get("/health")).json()
    services = data["services"]
    assert "database" in services
    assert "redis" in services


async def test_health_db_conectado(client):
    data = (await client.get("/health")).json()
    assert data["services"]["database"] == "connected"
