#!/usr/bin/env python3
"""
Simula o fluxo completo (lead → chat → plano) contra a API local
e imprime o payload JSON exato que seria enviado ao webhook Make.

Uso:
    python scripts/test_webhook_payload.py
    python scripts/test_webhook_payload.py --base-url http://meuserver:8000
"""
import argparse
import json
import sys
import time

import httpx

DEFAULT_BASE_URL = "http://localhost:8000"
API = "/api/v1"

LEAD_DATA = {
    "tipo_negocio": "B2B",
    "segmento": "Tecnologia",
    "empresa": "TechBrasil Soluções Ltda",
    "porte": "EPP",
    "colaboradores": "51-200",
    "cidade": "Curitiba",
    "estado": "PR",
    "nome_contato": "Marina Costa",
    "email": f"marina.teste.{int(time.time())}@techbrasil.com.br",
    "whatsapp": "41988887777",
    "cargo": "Gerente de Operações",
    "usa_monday": "avaliando",
    "areas_interesse": ["Vendas", "Projetos", "Suporte"],
    "dor_principal": "Controle de projetos descentralizado em planilhas, sem visibilidade de prazos e gargalos",
}

CHAT_MESSAGES = [
    "Temos cerca de 15 projetos simultâneos e não conseguimos acompanhar prazos. Tudo fica em planilhas do Google.",
    "O time de vendas também precisa de um CRM melhor. Hoje usam um sistema legado que não integra com nada.",
]


def _url(base: str, path: str) -> str:
    return f"{base.rstrip('/')}{API}{path}"


def main():
    parser = argparse.ArgumentParser(description="Testa fluxo completo e mostra payload Make")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help=f"URL base da API (default: {DEFAULT_BASE_URL})")
    args = parser.parse_args()
    base = args.base_url

    client = httpx.Client(timeout=60.0)

    # 1. Health check
    print("═" * 60)
    print("1. Health check...")
    try:
        r = client.get(_url(base, "/../health"))
        # fallback: /api/v1 prefix may not apply to /health
        if r.status_code != 200:
            r = client.get(f"{base.rstrip('/')}/health")
        if r.status_code != 200:
            r = client.get(f"{base.rstrip('/')}/api/v1/health")
        print(f"   Status: {r.status_code}")
        if r.status_code != 200:
            print(f"   WARN: health check retornou {r.status_code}, continuando mesmo assim...")
    except httpx.ConnectError:
        print(f"   ERRO: Não foi possível conectar a {base}")
        print("   Certifique-se de que a API está rodando.")
        sys.exit(1)

    # 2. Criar lead
    print("\n2. Criando lead...")
    r = client.post(_url(base, "/leads"), json=LEAD_DATA)
    if r.status_code != 201:
        print(f"   ERRO ao criar lead: {r.status_code}")
        print(f"   {r.text}")
        sys.exit(1)
    lead = r.json()
    lead_id = lead["id"]
    print(f"   Lead criado: {lead_id}")
    print(f"   Empresa: {lead['empresa']}")

    # 3. Iniciar chat
    print("\n3. Iniciando sessão de chat...")
    r = client.post(_url(base, "/chat/start"), json={"lead_id": lead_id})
    if r.status_code != 201:
        print(f"   ERRO ao iniciar chat: {r.status_code} — {r.text}")
        sys.exit(1)
    chat = r.json()
    session_id = chat["session_id"]
    print(f"   Session: {session_id}")
    print(f"   Greeting: {chat.get('greeting', '')[:100]}...")

    # 4. Enviar mensagens
    for i, msg in enumerate(CHAT_MESSAGES, 1):
        print(f"\n4.{i}. Enviando mensagem {i}...")
        r = client.post(
            _url(base, "/chat/message"),
            json={"session_id": session_id, "content": msg},
        )
        if r.status_code != 200:
            print(f"   ERRO: {r.status_code} — {r.text}")
            sys.exit(1)
        resp = r.json()
        print(f"   Resposta: {resp.get('response', '')[:100]}...")

    # 5. Encerrar chat (dispara geração do plano)
    print("\n5. Encerrando chat...")
    r = client.post(_url(base, "/chat/end"), json={"session_id": session_id})
    if r.status_code != 200:
        print(f"   ERRO ao encerrar chat: {r.status_code} — {r.text}")
        sys.exit(1)
    end_data = r.json()
    # plan_id vem dentro de plan_trigger.poll_url: "/api/v1/plans/status/{plan_id}"
    plan_trigger = end_data.get("plan_trigger")
    if not plan_trigger or not plan_trigger.get("poll_url"):
        print("   WARN: Nenhum plan_trigger retornado. O plano pode não ter sido criado.")
        print(f"   Response: {json.dumps(end_data, indent=2)}")
        sys.exit(1)
    plan_id = plan_trigger["poll_url"].rsplit("/", 1)[-1]
    print(f"   Plan ID: {plan_id}")

    # 6. Polling do status do plano
    print("\n6. Aguardando geração do plano (pode levar até 3 min)...")
    max_polls = 90  # 90 x 2s = 180s
    for attempt in range(max_polls):
        r = client.get(_url(base, f"/plans/status/{plan_id}"))
        if r.status_code != 200:
            print(f"   ERRO no polling: {r.status_code} — {r.text}")
            sys.exit(1)
        status_data = r.json()
        plan_status = status_data.get("status", "unknown")
        if attempt % 5 == 0 or plan_status != "generating":
            print(f"   [{attempt + 1}/{max_polls}] Status: {plan_status}")

        if plan_status == "generated":
            print("   Plano gerado com sucesso!")
            break
        if plan_status == "error":
            print("   ERRO: Geração do plano falhou.")
            print(f"   Detalhes: {json.dumps(status_data, indent=2, ensure_ascii=False)}")
            sys.exit(1)
        time.sleep(2)
    else:
        print("   TIMEOUT: Plano não ficou pronto após 180s.")
        print(f"   Último status: {json.dumps(status_data, indent=2, ensure_ascii=False)}")
        print("   Verifique os logs da API: docker compose logs api --tail 50")
        sys.exit(1)

    # 7. Buscar plano completo
    print("\n7. Buscando plano completo...")
    r = client.get(_url(base, f"/plans/{plan_id}"))
    if r.status_code != 200:
        print(f"   ERRO ao buscar plano: {r.status_code} — {r.text}")
        sys.exit(1)
    plan_data = r.json()

    # 8. Buscar lead completo para montar payload
    r = client.get(_url(base, f"/leads/{lead_id}"))
    if r.status_code != 200:
        print(f"   ERRO ao buscar lead: {r.status_code} — {r.text}")
        sys.exit(1)
    lead_detail = r.json()

    # 9. Montar payload idêntico ao _notify_make()
    view_url = f"{base.rstrip('/')}/api/v1/plans/{plan_id}/view"
    download_url = f"{base.rstrip('/')}/api/v1/plans/{plan_id}/download"

    webhook_payload = {
        "lead_id": lead_id,
        "empresa": lead_detail["empresa"],
        "nome_contato": lead_detail["nome_contato"],
        "email": lead_detail["email"],
        "whatsapp": lead_detail.get("whatsapp") or "",
        "segmento": lead_detail["segmento"],
        "tipo_negocio": lead_detail["tipo_negocio"],
        "porte": lead_detail["porte"],
        "score": lead_detail["score"],
        "areas_interesse": lead_detail.get("areas_interesse") or [],
        "plan_id": str(plan_data["id"]),
        "plan_view_url": view_url,
        "plan_download_url": download_url,
        "summary": plan_data.get("summary") or {},
    }

    # 10. Output
    print("\n" + "═" * 60)
    print("PAYLOAD MAKE WEBHOOK (idêntico ao _notify_make)")
    print("═" * 60)
    print(json.dumps(webhook_payload, indent=2, ensure_ascii=False))
    print("═" * 60)
    print(f"\nView URL:     {view_url}")
    print(f"Download URL: {download_url}")
    print(f"\nPlano MD ({len(plan_data.get('content_md', ''))} chars):")
    content_preview = plan_data.get("content_md", "")[:500]
    print(content_preview)
    if len(plan_data.get("content_md", "")) > 500:
        print("... [truncado]")
    print("\nDone!")


if __name__ == "__main__":
    main()
