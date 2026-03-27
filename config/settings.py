# Runtime settings (env, feature flags, pipeline params).
# Load from env; no API keys in code.
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None  # type: ignore[misc, assignment]


def _load_env() -> None:
    if load_dotenv is None:
        return
    # Load from current working directory
    load_dotenv()
    # If running from project root, also try news-agent/.env
    cwd = Path.cwd()
    if (cwd / "news-agent" / ".env").exists():
        load_dotenv(cwd / "news-agent" / ".env")
    elif (cwd / ".env").exists():
        load_dotenv(cwd / ".env")


@dataclass(frozen=True)
class Settings:
    """Runtime settings loaded from environment."""

    guardian_api_key: str
    newsapi_key: str
    db_path: str
    openai_api_key: str  # Optional: OpenAI for headline/body/bias (fallback if no Anthropic key)
    anthropic_api_key: str  # Optional: Anthropic Claude for headline/body/bias (preferred)
    # Pipeline options (optional, with defaults)
    top_n_stories: int
    pipeline_hours_lookback: int
    # Max items to run through translate + cluster (0 = no cap). Speeds up pipeline when DB is large.
    pipeline_max_items: int
    # Days of raw items to keep in DB (older rows pruned on each run). Default 3.
    db_keep_days: int

    @classmethod
    def from_env(cls) -> Settings:
        _load_env()
        return cls(
            guardian_api_key=os.getenv("GUARDIAN_API_KEY", "").strip(),
            newsapi_key=os.getenv("NEWSAPI_KEY", "").strip(),
            db_path=os.getenv("DB_PATH", "").strip() or str(Path.cwd() / "data" / "news_agent.db"),
            openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", "").strip(),
            top_n_stories=int(os.getenv("TOP_N_STORIES", "20")),
            pipeline_hours_lookback=int(os.getenv("PIPELINE_HOURS_LOOKBACK", "48")),
            pipeline_max_items=int(os.getenv("PIPELINE_MAX_ITEMS", "3000")),
            db_keep_days=int(os.getenv("DB_KEEP_DAYS", "3")),
        )


_settings: Settings | None = None


def get_settings() -> Settings:
    """Return cached settings loaded from env. Loads on first call."""
    global _settings
    if _settings is None:
        _settings = Settings.from_env()
    return _settings
