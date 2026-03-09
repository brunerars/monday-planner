from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Database ─────────────────────────────────────────────
    database_url: str = Field(
        default="postgresql+asyncpg://mondayplanner:mondayplanner@localhost:5432/mondayplanner"
    )

    # ── Redis ─────────────────────────────────────────────────
    redis_url: str = Field(default="redis://localhost:6379/0")

    # ── Claude API ────────────────────────────────────────────
    claude_api_key: str = Field(default="")
    claude_model: str = Field(default="claude-sonnet-4-20250514")

    # ── Make (webhook de notificação) ─────────────────────────
    # Webhook do Make que recebe dados do lead + link do plano
    # e cria o item no board de pipeline da Monday + envia email ao lead
    make_webhook_url: str = Field(default="")

    # ── Segurança ─────────────────────────────────────────────
    internal_api_key: str = Field(default="")

    # ── CORS ──────────────────────────────────────────────────
    cors_origins: str = Field(default="http://localhost:3000,http://localhost:5500")

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    # ── Ambiente ──────────────────────────────────────────────
    environment: str = Field(default="development")
    log_level: str = Field(default="debug")
    api_base_url: str = Field(default="http://localhost:8000")

    # ── Agente ────────────────────────────────────────────────
    agent_max_messages: int = Field(default=15)
    agent_max_input_tokens: int = Field(default=500)
    agent_max_output_tokens: int = Field(default=800)
    agent_context_window: int = Field(default=8)
    agent_session_timeout_minutes: int = Field(default=30)

    # ── Rate Limiting ─────────────────────────────────────────
    rate_limit_per_session: int = Field(default=3)
    rate_limit_per_session_window_seconds: int = Field(default=60)
    rate_limit_global: int = Field(default=100)
    rate_limit_global_window_seconds: int = Field(default=60)

    # ── CTA ───────────────────────────────────────────────────
    cta_calendly_url: str = Field(default="https://calendly.com/seulink/mondayplanner")


settings = Settings()
