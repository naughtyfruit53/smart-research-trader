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

    # Feature engineering configuration
    FEATURE_LOOKBACK_DAYS: int = 400
    FUND_FFILL_DAYS: int = 120
    COMPOSITE_WEIGHTS: str = '{"quality": 0.25, "valuation": 0.25, "momentum": 0.25, "sentiment": 0.25}'
    SECTOR_MAP_PATH: str = ""
    ENABLE_FEATURES_TASK: bool = False


settings = Settings()


def get_composite_weights() -> dict[str, float]:
    """Parse composite weights from config.
    
    Returns:
        Dictionary with weights for quality, valuation, momentum, sentiment
    """
    import json
    try:
        weights = json.loads(settings.COMPOSITE_WEIGHTS)
        # Ensure all required keys exist with defaults
        return {
            "quality": weights.get("quality", 0.25),
            "valuation": weights.get("valuation", 0.25),
            "momentum": weights.get("momentum", 0.25),
            "sentiment": weights.get("sentiment", 0.25),
        }
    except json.JSONDecodeError:
        # Return defaults if parsing fails
        return {"quality": 0.25, "valuation": 0.25, "momentum": 0.25, "sentiment": 0.25}


def load_sector_mapping() -> dict[str, str] | None:
    """Load optional sector mapping from file.
    
    Returns:
        Dictionary mapping ticker to sector, or None if not available
    """
    if not settings.SECTOR_MAP_PATH:
        return None
    
    try:
        import json
        from pathlib import Path
        
        path = Path(settings.SECTOR_MAP_PATH)
        if not path.exists():
            return None
            
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return None
