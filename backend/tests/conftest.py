import pytest
from unittest.mock import AsyncMock, patch


@pytest.fixture
def mock_session():
    """Provides a mock AsyncSession for unit tests that don't need a real DB."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    return session
