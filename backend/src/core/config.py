"""Application configuration using pydantic-settings."""

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    model_config = ConfigDict(env_file=".env", case_sensitive=True)

    APP_ENV: str = "development"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]
    LOG_LEVEL: str = "INFO"


settings = Settings()
