"""MCP protocol validation — list tools/resources/prompts over an in-memory FastMCP client.

This exercises the real MCP protocol surface (not internal attrs), so it asserts the server
actually exposes the documented 6 tools, 6 resources, and 1 prompt to any MCP client.
"""
import pytest

pytest.importorskip("fastmcp")

import mcp_server  # noqa: E402

EXPECTED_TOOLS = {
    "query_kpis", "get_company_health", "detect_kpi_anomalies",
    "forecast_metric", "list_available_metrics", "get_executive_summary",
}


async def _list(kind: str):
    from fastmcp import Client
    async with Client(mcp_server.mcp) as c:
        if kind == "tools":
            return await c.list_tools()
        if kind == "resources":
            return await c.list_resources()
        return await c.list_prompts()


@pytest.mark.asyncio
async def test_six_tools_exposed():
    tools = await _list("tools")
    names = {t.name for t in tools}
    assert EXPECTED_TOOLS.issubset(names), f"missing: {EXPECTED_TOOLS - names}"


@pytest.mark.asyncio
async def test_resources_and_prompt_exposed():
    resources = await _list("resources")
    prompts = await _list("prompts")
    # 6 kpi://<domain>/latest resources + the monthly briefing prompt
    assert len(resources) >= 6, f"expected >=6 resources, got {len(resources)}"
    assert len(prompts) >= 1, f"expected >=1 prompt, got {len(prompts)}"
