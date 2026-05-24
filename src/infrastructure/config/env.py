import os

from pydantic import Field
from pydantic_settings import BaseSettings


def _asyncpg_url(url: str) -> str:
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


class EnvironSettings(BaseSettings):
    # Infrastructure
    DATABASE_URL: str = _asyncpg_url(
        os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres",
        )
    )

    # API
    SECRET_KEY: str = Field(default="dummy-value")
    ENVIRONMENT: str = Field(default="development")
    ALLOWED_ORIGINS: str = Field(default="http://localhost:3000")
