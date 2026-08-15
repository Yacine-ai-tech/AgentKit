import pytest
import httpx
from fastapi.testclient import TestClient
from agentkit_mcp.web_app import build_app
import os

app = build_app()
client = TestClient(app)
HEADERS = {"X-AgentKit-Internal-Token": os.getenv("AGENTKIT_INTERNAL_TOKEN", "")}

@pytest.mark.asyncio
async def test_e2e_agentkit_mcp_tools_list():
    # Test the MCP Server capabilities discovery endpoint
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/tools", headers=HEADERS)
        assert response.status_code == 200
        data = response.json()
        assert "tools" in data
        assert len(data["tools"]) >= 5

@pytest.mark.asyncio
async def test_e2e_agentkit_mcp_execute_query():
    # Test KPI metrics endpoint
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/kpis?domain=Finance", headers=HEADERS)
        # Should return 200 or 503 if DB is not seeded
        assert response.status_code in (200, 400, 503)

@pytest.mark.asyncio
async def test_e2e_agentkit_mcp_execute_anomaly():
    # Test anomaly detection endpoint
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/anomalies?domain=Finance", headers=HEADERS)
        assert response.status_code in (200, 400, 503)
