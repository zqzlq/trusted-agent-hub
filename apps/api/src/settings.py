"""Environment-backed runtime settings for the Consumer API.

Loads .env from the project root (apps/api/.env) and overrides with
process environment variables (os.environ wins over .env).
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import os

_ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


def _load_dotenv() -> None:
    """Parse apps/api/.env into os.environ, without overwriting existing vars."""
    if not _ENV_FILE.is_file():
        return
    for raw in _ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and (key not in os.environ or not os.environ[key]):
            os.environ[key] = value


# Load once at import time.
_load_dotenv()


@dataclass(frozen=True, slots=True)
class Settings:
    """Immutable settings loaded from the process environment."""

    database_url: str | None = None
    allow_insecure_user_header: bool = False

    @classmethod
    def from_environment(cls) -> "Settings":
        database_url = os.getenv("DATABASE_URL")
        if database_url is not None:
            database_url = database_url.strip() or None
        allow_header = os.getenv(
            "CONSUMER_ALLOW_INSECURE_USER_HEADER", ""
        ).strip().lower()
        return cls(
            database_url=database_url,
            allow_insecure_user_header=allow_header == "true",
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return process-wide settings."""
    return Settings.from_environment()


def clear_settings_cache() -> None:
    """Forget cached environment settings (primarily for tests)."""
    get_settings.cache_clear()
