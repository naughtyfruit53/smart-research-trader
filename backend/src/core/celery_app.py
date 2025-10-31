"""Celery app factory and configuration."""

import logging

from celery import Celery
from celery.signals import after_setup_logger

from src.core.config import settings

logger = logging.getLogger(__name__)


def create_celery_app() -> Celery:
    """Create and configure Celery application."""
    app = Celery(
        "smart_trader",
        broker=settings.CELERY_BROKER_URL,
        backend=settings.CELERY_RESULT_BACKEND,
    )

    app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_time_limit=3600,  # 1 hour
        task_soft_time_limit=3000,  # 50 minutes
        worker_prefetch_multiplier=1,
        worker_max_tasks_per_child=1000,
    )

    # Autodiscover tasks from data.etl package
    app.autodiscover_tasks(["src.data.etl"])

    return app


@after_setup_logger.connect
def setup_loggers(logger, *args, **kwargs):
    """Setup JSON logging for Celery."""
    formatter = logging.Formatter(
        '{"time": "%(asctime)s", "name": "%(name)s", "level": "%(levelname)s", '
        '"message": "%(message)s"}'
    )
    for handler in logger.handlers:
        handler.setFormatter(formatter)


# Create the Celery app instance
celery_app = create_celery_app()
