import asyncio
import os

import pytest

os.environ.setdefault("POSTGRES_URL", "postgresql://fake:fake@localhost/fake")

from agentkit_mcp import mcp_server as ms  # noqa: E402


@pytest.mark.skipif(not ms._FASTMCP, reason="fastmcp not installed")
def test_mcp_resources_match_real_seeded_domains():
    """Real bug: README previously advertised MCP resources for domains ("Growth",
    "ESG", "IT_Ops") that don't exist anywhere in this project's own seed data
    (src/data/seed.py's BUSINESS_KPIS) -- and the resources themselves were never
    actually implemented at all. Both are fixed: 5 resources, one per real domain."""
    resources = asyncio.run(ms.mcp.list_resources())
    uris = {str(r.uri) for r in resources}
    expected = {f"kpi://{d}/latest" for d in ("Finance", "People", "Operations", "Customer", "Engineering")}
    assert uris == expected


@pytest.mark.skipif(not ms._FASTMCP, reason="fastmcp not installed")
def test_mcp_prompt_registered():
    prompts = asyncio.run(ms.mcp.list_prompts())
    names = {p.name for p in prompts}
    assert "monthly_executive_briefing" in names
