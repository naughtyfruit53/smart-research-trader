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
    # Default DATABASE_URL for local development. Override via environment variable in production.
    DATABASE_URL: str = "postgresql://trader:trader_dev_pass@localhost:5432/smart_trader"

    # Celery configuration
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # Data provider configuration
    PRICE_PROVIDER: str = "yf"  # yf or nse
    FUND_CSV_PATH: str = ""
    NEWS_PROVIDER: str = "rss"  # rss or gdelt

    # Feature flags
    ENABLE_FINBERT: bool = False
    SKIP_NETWORK_IN_TESTS: bool = False

    # Ticker list for data ingestion (comma-separated)
    TICKERS: str = "RELIANCE.NS,TCS.NS,INFY.NS,HDFCBANK.NS,ICICIBANK.NS"

    # Batch configuration
    PRICE_FETCH_BATCH_SIZE: int = 5
    NEWS_FETCH_BATCH_SIZE: int = 10
    FUNDAMENTAL_FETCH_BATCH_SIZE: int = 10


settings = Settings()
