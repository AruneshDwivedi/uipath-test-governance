"""Application configuration.

All config is loaded from environment variables with sensible defaults
for local development. In production (UiPath Automation Cloud), these
are set as environment attributes.

[STATED] No secrets in config files. All credentials come from
environment variables or UiPath Orchestrator assets.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class DatabaseConfig:
    host: str = os.getenv("DB_HOST", "localhost")
    port: int = int(os.getenv("DB_PORT", "5432"))
    name: str = os.getenv("DB_NAME", "test_governance")
    user: str = os.getenv("DB_USER", "postgres")
    password: str = os.getenv("DB_PASSWORD", "")

    @property
    def url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.name}"
        )


@dataclass
class UiPathConfig:
    base_url: str = os.getenv("UIPATH_BASE_URL", "https://cloud.uipath.com")
    org_id: str = os.getenv("UIPATH_ORG_ID", "")
    tenant_id: str = os.getenv("UIPATH_TENANT_ID", "")
    client_id: str = os.getenv("UIPATH_CLIENT_ID", "")
    client_secret: str = os.getenv("UIPATH_CLIENT_SECRET", "")
    folder_id: str = os.getenv("UIPATH_FOLDER_ID", "")


@dataclass
class LLMConfig:
    provider: str = os.getenv("LLM_PROVIDER", "openai")
    model: str = os.getenv("LLM_MODEL", "gpt-4o")
    api_key: str = os.getenv("LLM_API_KEY", "")
    temperature: float = 0.1


@dataclass
class AppConfig:
    env: str = os.getenv("APP_ENV", "development")
    debug: bool = os.getenv("APP_DEBUG", "true").lower() == "true"
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    db: DatabaseConfig = field(default_factory=DatabaseConfig)
    uipath: UiPathConfig = field(default_factory=UiPathConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
