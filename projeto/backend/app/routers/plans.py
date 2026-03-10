"""
Plans router — endpoints de acesso ao planejamento.md.

GET /plans/status/{plan_id}   → polling de status da geração
GET /plans/{plan_id}          → buscar plano completo
GET /plans/{plan_id}/download → download do arquivo .md
"""
import re
import uuid

import markdown2
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

import app.services.plan_service as plan_service
from app.config import settings
from app.dependencies import get_db
from app.schemas.plan import PlanResponse, PlanStatusResponse, PlanSummary

router = APIRouter()


def _plan_url(plan_id: uuid.UUID) -> str:
    return f"/api/v1/plans/{plan_id}"


def _download_url(plan_id: uuid.UUID) -> str:
    return f"/api/v1/plans/{plan_id}/download"


def _safe_filename(empresa: str) -> str:
    """Gera nome de arquivo seguro a partir do nome da empresa."""
    slug = re.sub(r"[^a-z0-9]+", "-", empresa.lower()).strip("-")
    return f"planejamento-{slug}.md"


# ── GET /plans/status/{plan_id} ───────────────────────────────────────────


@router.get(
    "/plans/status/{plan_id}",
    response_model=PlanStatusResponse,
    summary="Status da geração do planejamento",
)
async def get_plan_status(
    plan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Polling de status. Chamar a cada 3s até status=completed ou status=error."""
    plan = await plan_service.get_plan_status(plan_id, db)
    if not plan:
        raise HTTPException(
            status_code=404,
            detail={"code": "PLAN_NOT_FOUND", "message": "Planejamento não encontrado"},
        )

    if plan.status == "generating":
        return PlanStatusResponse(
            plan_id=plan.id,
            status="generating",
            progress_percent=50,
            estimated_seconds_remaining=10,
        )

    if plan.status == "generated":
        return PlanStatusResponse(
            plan_id=plan.id,
            status="completed",
            plan_url=_plan_url(plan.id),
            download_url=_download_url(plan.id),
        )

    # status == "error"
    return PlanStatusResponse(
        plan_id=plan.id,
        status="error",
        message="Erro ao gerar planejamento. Nosso time foi notificado.",
    )


# ── GET /plans/{plan_id} ──────────────────────────────────────────────────


@router.get(
    "/plans/{plan_id}",
    response_model=PlanResponse,
    summary="Buscar planejamento completo",
)
async def get_plan(
    plan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Retorna o planejamento gerado com conteúdo markdown e resumo estruturado."""
    plan = await plan_service.get_plan(plan_id, db)
    if not plan:
        raise HTTPException(
            status_code=404,
            detail={"code": "PLAN_NOT_FOUND", "message": "Planejamento não encontrado"},
        )

    if plan.status == "generating":
        raise HTTPException(
            status_code=202,
            detail={
                "code": "PLAN_GENERATING",
                "message": "Planejamento ainda sendo gerado",
                "poll_url": f"/api/v1/plans/status/{plan_id}",
            },
        )

    if plan.status == "error":
        raise HTTPException(
            status_code=500,
            detail={"code": "PLAN_ERROR", "message": "Erro na geração do planejamento"},
        )

    summary = None
    if plan.summary_json:
        try:
            summary = PlanSummary(**plan.summary_json)
        except Exception:
            summary = None

    return PlanResponse(
        id=plan.id,
        lead_id=plan.lead_id,
        empresa=plan.empresa,
        version=plan.version,
        status=plan.status,
        content_md=plan.content_md,
        summary=summary,
        created_at=plan.created_at,
        download_url=_download_url(plan.id),
        cta_url=settings.cta_calendly_url,
    )


# ── GET /plans/{plan_id}/view ─────────────────────────────────────────────

_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Planejamento — {empresa}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter+Tight:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
  :root {{
    --almost-black: #111;
    --red: #c82a2a;
    --red-dark: #a52222;
    --text: #111;
    --text-secondary: #555;
    --muted: #888;
    --border: #e5e5e5;
    --bg: #f7f7f7;
    --white: #fff;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: "Inter Tight", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.7;
    padding: clamp(1rem, 4vw, 2.5rem) clamp(.75rem, 3vw, 1.5rem);
  }}
  .accent-bar {{
    position: fixed;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: linear-gradient(90deg, var(--red), #6161ff);
    z-index: 100;
  }}
  .wrapper {{
    max-width: 800px;
    margin: 0 auto;
    background: var(--white);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: clamp(2rem, 5vw, 3.5rem) clamp(1.5rem, 5vw, 3.5rem);
    box-shadow: 0 1px 3px rgba(0,0,0,.06), 0 8px 32px rgba(0,0,0,.04);
  }}
  .badge {{
    display: inline-flex;
    align-items: center;
    gap: .4rem;
    background: var(--almost-black);
    color: var(--white);
    font-size: .65rem;
    font-weight: 700;
    letter-spacing: .08em;
    text-transform: uppercase;
    padding: .3rem .85rem;
    border-radius: 999px;
    margin-bottom: 1.75rem;
  }}
  .badge-dot {{
    width: 6px; height: 6px;
    border-radius: 50%;
    background: var(--red);
  }}
  h1 {{
    font-size: clamp(1.5rem, 4vw, 1.9rem);
    font-weight: 800;
    line-height: 1.2;
    letter-spacing: -.03em;
    margin-bottom: .5rem;
    color: var(--almost-black);
  }}
  h2 {{
    font-size: clamp(1.05rem, 2.5vw, 1.25rem);
    font-weight: 700;
    margin: 2.5rem 0 .75rem;
    padding-bottom: .5rem;
    border-bottom: 2px solid var(--almost-black);
    color: var(--almost-black);
  }}
  h3 {{
    font-size: 1rem;
    font-weight: 700;
    margin: 1.5rem 0 .5rem;
    color: var(--almost-black);
  }}
  p {{ margin-bottom: 1rem; color: var(--text-secondary); }}
  ul, ol {{ padding-left: 1.5rem; margin-bottom: 1rem; }}
  li {{ margin-bottom: .35rem; color: var(--text-secondary); }}
  hr {{ border: none; border-top: 1px solid var(--border); margin: 2rem 0; }}
  strong {{ font-weight: 700; color: var(--almost-black); }}
  code {{
    background: var(--bg);
    padding: .15em .4em;
    border-radius: 4px;
    font-size: .88em;
    border: 1px solid var(--border);
  }}
  blockquote {{
    border-left: 3px solid var(--red);
    padding-left: 1rem;
    color: var(--muted);
    margin: 1rem 0;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 1rem;
    font-size: .9rem;
  }}
  th, td {{
    padding: .6rem .8rem;
    text-align: left;
    border-bottom: 1px solid var(--border);
  }}
  th {{
    font-weight: 700;
    color: var(--almost-black);
    background: var(--bg);
  }}
  .cta {{
    margin-top: 3rem;
    padding: 2.5rem 2rem;
    background: var(--almost-black);
    border-radius: 14px;
    text-align: center;
    position: relative;
    overflow: hidden;
  }}
  .cta::before {{
    content: '';
    position: absolute;
    inset: 0;
    background:
      radial-gradient(ellipse 60% 50% at 20% 80%, rgba(200,42,42,.15) 0%, transparent 70%),
      radial-gradient(ellipse 50% 60% at 80% 20%, rgba(97,97,255,.12) 0%, transparent 70%);
    pointer-events: none;
  }}
  .cta p {{
    margin-bottom: 1.25rem;
    font-size: 1.05rem;
    color: rgba(255,255,255,.85);
    position: relative;
  }}
  .cta a {{
    display: inline-block;
    background: var(--red);
    color: var(--white);
    font-family: "Inter Tight", sans-serif;
    font-weight: 700;
    font-size: .9rem;
    padding: .8rem 2.25rem;
    border-radius: 999px;
    text-decoration: none;
    transition: background .2s, transform .15s;
    position: relative;
  }}
  .cta a:hover {{
    background: var(--red-dark);
    transform: translateY(-1px);
  }}
  .footer {{
    margin-top: 2.5rem;
    padding-top: 1.5rem;
    border-top: 1px solid var(--border);
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    font-size: .75rem;
    color: var(--muted);
  }}
  .footer-logo {{
    font-weight: 800;
    font-size: .7rem;
    letter-spacing: .08em;
    text-transform: uppercase;
    color: var(--almost-black);
  }}
  @media (max-width: 600px) {{
    .wrapper {{ border-radius: 12px; }}
    h1 {{ letter-spacing: -.02em; }}
    .cta {{ padding: 2rem 1.25rem; }}
    .footer {{ flex-direction: column; text-align: center; gap: .5rem; }}
  }}
</style>
</head>
<body>
<div class="accent-bar"></div>
<div class="wrapper">
  <span class="badge"><span class="badge-dot"></span> MondayPlanner</span>
  {content}
  <div class="cta">
    <p>Pronto para dar o pr&oacute;ximo passo?</p>
    <a href="{cta_url}" target="_blank" rel="noopener">Agendar call com especialista</a>
  </div>
  <div class="footer">
    <span class="footer-logo">MondayPlanner</span>
    <span>Documento confidencial &middot; Gerado por IA</span>
  </div>
</div>
</body>
</html>"""


@router.get(
    "/plans/{plan_id}/view",
    response_class=HTMLResponse,
    summary="Visualizar planejamento como página HTML",
)
async def view_plan(
    plan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Renderiza o planejamento como página HTML estilizada.
    Este é o link enviado ao lead via email pelo Make.
    """
    plan = await plan_service.get_plan(plan_id, db)
    if not plan:
        raise HTTPException(
            status_code=404,
            detail={"code": "PLAN_NOT_FOUND", "message": "Planejamento não encontrado"},
        )

    if plan.status != "generated":
        raise HTTPException(
            status_code=404,
            detail={"code": "PLAN_NOT_READY", "message": "Planejamento ainda não disponível"},
        )

    content_html = markdown2.markdown(
        plan.content_md,
        extras=["fenced-code-blocks", "tables", "strike", "break-on-newline"],
    )

    page = _HTML_TEMPLATE.format(
        empresa=plan.empresa,
        content=content_html,
        cta_url=settings.cta_calendly_url,
    )

    return HTMLResponse(content=page)


# ── GET /plans/{plan_id}/download ─────────────────────────────────────────


@router.get(
    "/plans/{plan_id}/download",
    summary="Download do planejamento como arquivo .md",
)
async def download_plan(
    plan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Retorna o arquivo markdown para download direto pelo browser."""
    plan = await plan_service.get_plan(plan_id, db)
    if not plan:
        raise HTTPException(
            status_code=404,
            detail={"code": "PLAN_NOT_FOUND", "message": "Planejamento não encontrado"},
        )

    if plan.status != "generated":
        raise HTTPException(
            status_code=404,
            detail={"code": "PLAN_NOT_READY", "message": "Planejamento ainda não disponível"},
        )

    filename = _safe_filename(plan.empresa)
    return Response(
        content=plan.content_md,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
