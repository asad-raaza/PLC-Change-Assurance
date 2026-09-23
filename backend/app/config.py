"""Runtime configuration. Secrets come from the environment, never from git."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "PLC Change Assurance"
    framework_version: str = "0.1.0"
    environment: str = "lab"

    # Enforcement is disabled unless BOTH flags are satisfied.
    operating_mode: str = "passive"  # passive | advisory | enforcement
    lab_mode: bool = False

    fail_safe_mode: str = "fail_to_advisory"  # fail_open | fail_closed | fail_to_advisory
    risk_policy_mode: str = "balanced"  # conservative | balanced | monitor-only | custom

    database_url: str = Field(default=f"sqlite:///{ROOT / 'data' / 'assurance.db'}")
    secret_key: str = "lab-only-change-me"
    access_token_expire_minutes: int = 480

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8080"

    embed_simulator: bool = True
    seed_on_startup: bool = True

    jwt_algorithm: str = "HS256"

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def enforcement_enabled(self) -> bool:
        return self.lab_mode and self.operating_mode.lower() == "enforcement"


@lru_cache
def get_settings() -> Settings:
    return Settings()
