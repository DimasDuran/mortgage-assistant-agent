"""Application settings, loaded from the environment and validated at startup."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed configuration. Fails fast at startup if required values are missing."""

    anthropic_api_key: str = Field(validation_alias="ANTHROPIC_API_KEY")

    model: str = "claude-sonnet-4-6"
    max_tokens: int = 1024
    # Hard cap on the agent's tool-calling loops; prevents runaway agents.
    max_steps: int = 8

    # Prompt source: code is the default (versioned, reviewed). Set to true to
    # pull the system prompt from the LangSmith Prompt Hub instead, with the code
    # constant as a fallback if the pull fails.
    use_prompt_hub: bool = False

    # API key for the HTTP API (read from VERA_API_KEY). If unset, auth is
    # disabled (development only); set it in production.
    api_key: str | None = None

    # Persistence: LangGraph checkpoint store (Postgres).
    # If set, conversation state survives restarts via PostgresSaver.
    # Uses the same Postgres instance as Supabase or a dedicated one.
    database_url: str | None = Field(default=None, validation_alias="DATABASE_URL")

    # Persistence: application data (Supabase Postgres).
    # If both are set, applications are stored in Supabase; otherwise in memory.
    supabase_url: str | None = Field(default=None, validation_alias="SUPABASE_URL")
    supabase_key: str | None = Field(default=None, validation_alias="SUPABASE_KEY")
    supabase_table: str = "applications"
    organizations_table: str = "organizations"

    # Auth (Supabase Auth). The JWT secret verifies access tokens issued by
    # Supabase; if unset, auth is disabled (development only) and requests run as
    # a local loan_officer (not super_admin). Audience is Supabase's default for
    # signed-in users.
    supabase_jwt_secret: str | None = Field(
        default=None, validation_alias="SUPABASE_JWT_SECRET"
    )
    supabase_jwt_audience: str = "authenticated"
    # Where the invitation email sends the user to set their password.
    auth_redirect_url: str | None = Field(
        default=None, validation_alias="VERA_AUTH_REDIRECT_URL"
    )

    # Sensitive data encryption key (Fernet, 32-byte base64). If set, sensitive
    # fields (SSN) are encrypted at the repository layer before storage.
    encryption_key: str | None = Field(
        default=None, validation_alias="VERA_ENCRYPTION_KEY"
    )

    # CORS: origins allowed to call the API (comma-separated in env). Defaults to
    # all origins for local development; restrict in production.
    allowed_origins: list[str] = ["*"]

    # Rate limiting for HTTP endpoints (requests per minute per client). Set to
    # 0 or a negative value to disable. The chat endpoint is the main target.
    rate_limit_per_minute: int = 10

    # Prompt caching. Enabled by default; disable if the model does not support it
    # or during testing.
    enable_cache: bool = True

    # Cost controls
    max_budget_per_session: float | None = Field(
        default=None, validation_alias="VERA_MAX_BUDGET_PER_SESSION"
    )
    max_tokens_per_turn: int | None = Field(
        default=None, validation_alias="VERA_MAX_TOKENS_PER_TURN"
    )

    # Conversation memory (short-term / long-term with summarization)
    # Trigger summarization when the message history exceeds this many turns.
    max_turns_before_summary: int = Field(
        default=6, validation_alias="VERA_MAX_TURNS_BEFORE_SUMMARY"
    )
    # Keep this many recent turns verbatim after summarization.
    keep_recent_turns: int = Field(
        default=2, validation_alias="VERA_KEEP_RECENT_TURNS"
    )

    # Evals (regression testing). The judge is a cheaper model; the threshold is
    # the minimum pass rate the suite must meet. eval_delay_seconds spaces calls
    # to respect the embedding provider's rate limit on the free tier.
    eval_judge_model: str = "claude-haiku-4-5"
    eval_threshold: float = 0.8
    eval_delay_seconds: float = 0.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="VERA_",
        extra="ignore",
        protected_namespaces=(),
    )


@lru_cache
def get_settings() -> Settings:
    """Return the settings as a cached singleton (read and validated once)."""
    return Settings()
