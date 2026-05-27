"""Shared pytest fixtures.

Tests historically created ``TestClient(app)`` at module scope, which never
triggers FastAPI's ``lifespan`` startup hook — so ``init_db()`` did not run
and SQLite tables were missing. This conftest initializes the schema once
per test session so route-level tests can hit the DB.

It also clears the file-backed response cache before each test, since the
dashboard/summary route caches its full response and that cache otherwise
bleeds across tests (an earlier test's response is returned to a later test
that monkeypatched a different cost calculator).
"""

from __future__ import annotations

import pytest


@pytest.fixture(scope="session", autouse=True)
def _initialize_database() -> None:
    """Create all tables once before any test runs."""
    from core.database import init_db

    init_db()


@pytest.fixture(autouse=True)
def _clear_response_cache() -> None:
    """Clear the on-disk response cache between tests."""
    from core.cache import clear_cache

    clear_cache()
    yield
    clear_cache()
