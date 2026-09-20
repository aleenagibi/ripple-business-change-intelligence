from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration."""

    APP_NAME: str = "Ripple"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = (
        "Enterprise Business Change Intelligence Platform"
    )

    API_PREFIX: str = "/api"

    DATABASE_URL: str = Field(...)

    STORAGE_ROOT: str = "storage/documents"

    JWT_SECRET_KEY: str = Field(...)
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()