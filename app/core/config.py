from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application identity
    APP_NAME: str = "SovereignShield Compliance Engine"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Database — async SQLite, WAL mode configured at connection time
    DATABASE_URL: str = "sqlite+aiosqlite:///./sovereign_shield.db"
    DB_ECHO: bool = False

    # Ollama local AI
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3:8b"
    OLLAMA_TIMEOUT_SECONDS: float = 30.0

    # RND mock registry
    SIMULATE_RND_TIMEOUT: bool = False
    RND_TIMEOUT_DURATION_SECONDS: float = 4.0
    RND_REQUEST_TIMEOUT_SECONDS: float = 2.0

    # Compliance pipeline SLA (milliseconds converted to seconds in engine)
    PIPELINE_TIMEOUT_SECONDS: float = 15.0

    # DNC seed data path (relative to project root)
    DNC_CSV_PATH: str = "data/mock_dnc_list.csv"

    # Federal TCPA safe-harbor calling window (HH:MM:SS, inclusive start / exclusive end)
    FEDERAL_CALL_START: str = "08:00:00"
    FEDERAL_CALL_END: str = "21:00:00"

    # State overrides — stored here for reference; authoritative values are DB-seeded
    FL_CALL_END: str = "20:00:00"
    CT_CALL_END: str = "20:00:00"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings: Settings = get_settings()
