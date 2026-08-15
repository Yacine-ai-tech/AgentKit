"""MCP protocol validation — list tools/resources/prompts over an in-memory FastMCP client.

This exercises the real MCP protocol surface (not internal attrs), asserting that the
server exposes its registered tools and that the resources/prompts endpoints are
queryable. The core server ships with 6 reference BI tools; resources and prompts
are supplied by tool packs at load time (none are hardcoded into the agnostic server).
"""
import pytest

pytest.importorskip("fastmcp")

from agentkit_mcp import mcp_server  # noqa: E402

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
    """AgentKit is domain-agnostic: the core server registers no hardcoded resources or
    prompts. Domain-specific resources and prompts are supplied by tool packs at load time.
    This test verifies the server starts cleanly and the MCP surface is queryable — a
    non-zero count indicates a pack was loaded; zero is valid for a base install.
    """
    resources = await _list("resources")
    prompts = await _list("prompts")
    # Both lists must be queryable without error; counts depend on loaded packs.
    assert isinstance(resources, list), "resources/list must return a list"
    assert isinstance(prompts, list), "prompts/list must return a list"

