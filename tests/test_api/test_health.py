import pytest


@pytest.mark.asyncio
async def test_health(async_client):
    resp = await async_client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "healthy"
    assert body["service"] == "octoflash-ai-backend"


@pytest.mark.asyncio
async def test_ready(async_client):
    resp = await async_client.get("/api/v1/ready")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ready"


@pytest.mark.asyncio
async def test_root(async_client):
    resp = await async_client.get("/")
    assert resp.status_code == 200
    assert "Octoflash" in resp.json()["message"]
