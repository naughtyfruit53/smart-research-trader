"""Celery tasks for scheduled ETL jobs."""

import logging
from datetime import datetime, timedelta

from celery import shared_task
from celery.schedules import crontab

from src.core.celery_app import celery_app
from src.data.etl.fetch_fundamentals import fetch_and_upsert_fundamentals
from src.data.etl.fetch_news import fetch_and_upsert_news
from src.data.etl.fetch_prices import fetch_and_upsert_prices

logger = logging.getLogger(__name__)


@shared_task(name="update_prices_daily")
def update_prices_daily():
    """Daily task to update price data for all configured tickers."""
    logger.info("Starting daily price update task")

    try:
        # Fetch last 7 days to ensure we catch any missed data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)

        result = fetch_and_upsert_prices(start_date=start_date, end_date=end_date)

        total = sum(v for v in result.values() if v > 0)
        logger.info(f"Daily price update completed: {total} total records")

        return {"status": "success", "records": total, "details": result}

    except Exception as e:
        logger.error(f"Daily price update failed: {e}")
        return {"status": "error", "error": str(e)}


@shared_task(name="update_news_daily")
def update_news_daily():
    """Daily task to fetch news and perform sentiment analysis."""
    logger.info("Starting daily news update task")

    try:
        # Fetch last 24 hours of news
        end_date = datetime.now()
        start_date = end_date - timedelta(days=1)

        result = fetch_and_upsert_news(start_date=start_date, end_date=end_date)

        logger.info(f"Daily news update completed: {result} records")

        return {"status": "success", "records": result}

    except Exception as e:
        logger.error(f"Daily news update failed: {e}")
        return {"status": "error", "error": str(e)}


@shared_task(name="update_fundamentals_weekly")
def update_fundamentals_weekly(csv_path: str | None = None):
    """Weekly task to import fundamental data from CSV."""
    logger.info("Starting weekly fundamentals update task")

    try:
        result = fetch_and_upsert_fundamentals(csv_path)

        logger.info(f"Weekly fundamentals update completed: {result} records")

        return {"status": "success", "records": result}

    except Exception as e:
        logger.error(f"Weekly fundamentals update failed: {e}")
        return {"status": "error", "error": str(e)}


# Configure beat schedule
celery_app.conf.beat_schedule = {
    "update-prices-daily": {
        "task": "update_prices_daily",
        "schedule": crontab(hour=22, minute=0),  # Run at 10 PM UTC daily
    },
    "update-news-daily": {
        "task": "update_news_daily",
        "schedule": crontab(hour=23, minute=0),  # Run at 11 PM UTC daily
    },
    "update-fundamentals-weekly": {
        "task": "update_fundamentals_weekly",
        "schedule": crontab(day_of_week=1, hour=1, minute=0),  # Run at 1 AM UTC on Mondays
    },
}
