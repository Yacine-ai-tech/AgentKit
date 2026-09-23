import asyncio
import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("POSTGRES_URL", "postgresql://fake:fake@localhost/fake")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agentkit_mcp import mcp_server as ms  # noqa: E402
from src.data.seed import BUSINESS_KPIS  # noqa: E402


@pytest.mark.skipif(not ms._FASTMCP, reason="fastmcp not installed")
def test_mcp_resources_match_real_seeded_domains():
    """Real bug: README previously advertised MCP resources for domains ("Growth",
    "ESG", "IT_Ops") that, at the time, didn't exist anywhere in this project's own
    seed data -- and the resources themselves were never actually implemented at all.
    Both are fixed, and the resource list is derived from the seed data directly
    (checked here against the same source of truth, not a hardcoded domain list) so
    this test can't drift out of sync as domains are added the way the README did."""
    resources = asyncio.run(ms.mcp.list_resources())
    uris = {str(r.uri) for r in resources}
    real_domains = [d for d in BUSINESS_KPIS if d not in ("Forecasting", "Anomalies")]
    assert len(real_domains) == 10  # locks in the "beyond IntelAI's 7" requirement
    expected = {f"kpi://{d}/latest" for d in real_domains}
    assert uris == expected


@pytest.mark.skipif(not ms._FASTMCP, reason="fastmcp not installed")
def test_mcp_prompt_registered():
    prompts = asyncio.run(ms.mcp.list_prompts())
    names = {p.name for p in prompts}
    assert "monthly_executive_briefing" in names
