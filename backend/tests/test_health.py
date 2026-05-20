"""Integration test for /health and /version endpoints."""

import pytest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient, ASGITransport


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_health_endpoint():
    with patch("app.main.get_redis", return_value=AsyncMock()):
        from app.main import app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_version_endpoint():
    with patch("app.main.get_redis", return_value=AsyncMock()):
        from app.main import app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/version")
            data = response.json()
            assert response.status_code == 200
            assert "version" in data
            assert "env" in data
