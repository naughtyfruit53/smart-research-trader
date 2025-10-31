"""Pytest fixtures for database tests."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.db.models import Base


@pytest.fixture(scope="function")
def db_session(request) -> Session:
    """Create a fresh database session for each test.

    Uses the same database as configured in settings but creates tables
    at the start of each test and drops them at the end.

    For migration tests, skip the drop/create cycle.
    """
    from src.core.config import settings

    # Create engine for test database
    engine = create_engine(settings.DATABASE_URL, echo=False)

    # Skip drop/create for migration tests
    is_migration_test = "test_migration" in request.node.name

    if not is_migration_test:
        # Drop all tables and recreate
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)

    # Create session
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()

    try:
        yield session
    finally:
        session.close()
        if not is_migration_test:
            Base.metadata.drop_all(bind=engine)
