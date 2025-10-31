"""Tests for database session management."""

from src.db.session import check_db_health, get_db, get_session


def test_get_db_dependency():
    """Test get_db FastAPI dependency."""
    gen = get_db()
    db = next(gen)
    assert db is not None

    # Clean up
    try:
        next(gen)
    except StopIteration:
        pass


def test_get_session_context_manager():
    """Test get_session context manager."""
    with get_session() as session:
        assert session is not None


def test_check_db_health():
    """Test database health check."""
    result = check_db_health()
    assert result is True
