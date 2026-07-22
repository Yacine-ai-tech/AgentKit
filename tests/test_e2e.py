import pytest
import httpx
from fastapi.testclient import TestClient
from agentkit_mcp.web_app import build_app
import os

app = build_app()
client = TestClient(app)
HEADERS = {"X-OmniIntel-Internal-Token": os.getenv("OMNIINTEL_INTERNAL_TOKEN", "default-dev-token")}

@pytest.mark.asyncio
async def test_e2e_agentkit_mcp_tools_list():
    # Test the MCP Server capabilities discovery endpoint
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/mcp/tools", headers=HEADERS)
        assert response.status_code == 200
        data = response.json()
        assert "tools" in data
        assert len(data["tools"]) > 3

@pytest.mark.asyncio
async def test_e2e_agentkit_mcp_execute_query():
    # Test tool execution endpoint
    payload = {
        "tool": "query_kpis",
        "arguments": {"metric": "revenue", "period": "2026Q3"}
    }
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/mcp/execute", json=payload, headers=HEADERS)
        # Should return 200 or 400 if DB is not seeded
        assert response.status_code in (200, 400)

@pytest.mark.asyncio
async def test_e2e_agentkit_mcp_execute_anomaly():
    # Test anomaly detection capability
    payload = {
        "tool": "detect_anomalies",
        "arguments": {"threshold": 1.5, "department": "Finance"}
    }
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/mcp/execute", json=payload, headers=HEADERS)
        assert response.status_code in (200, 400)
