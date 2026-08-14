"""
AgentKit demo — orchestration via the Claude Agent SDK.

Exposes AgentKit's BI tools to Claude as an in-process SDK MCP server, then lets Claude
plan + call them to answer a business question.

Requirements (the Claude Agent SDK runs on top of the Claude Code CLI):
  - pip install claude-agent-sdk
  - npm i -g @anthropic-ai/claude-code   (the SDK spawns the `claude` CLI as its runtime)
  - ANTHROPIC_API_KEY set

Run:  python demos/claude_agent_sdk_demo.py
"""
from __future__ import annotations

import asyncio
import os

from agentkit_mcp.core.logger import get_logger

log = get_logger(__name__)

try:
    from claude_agent_sdk import (  # type: ignore
        ClaudeAgentOptions,
        create_sdk_mcp_server,
        query,
        tool,
    )
    _SDK = True
except ImportError:
    _SDK = False
    log.warning("claude_agent_sdk not installed — demo unavailable")

from agentkit_mcp.mcp_server import get_company_health, query_kpis, detect_kpi_anomalies, forecast_metric, list_available_metrics, get_executive_summary  # noqa: E402


if _SDK:
    @tool("get_company_health", "Composite company health index (score + interpretation).",
          {"domain": str})
    async def _health(args):
        res = await get_company_health(domain=args.get("domain") or None)
        return {"content": [{"type": "text", "text": str(res)}]}

    @tool("query_kpis", "Latest KPI metrics for a business domain.", {"domain": str, "limit": int})
    async def _kpis(args):
        res = await query_kpis(domain=args.get("domain") or "Finance", limit=int(args.get("limit", 20)))
        return {"content": [{"type": "text", "text": str(res)}]}

    @tool("detect_kpi_anomalies", "Find anomalies in a domain's KPI history.", {"domain": str, "method": str, "threshold": float})
    async def _anomalies(args):
        res = await detect_kpi_anomalies(domain=args.get("domain") or "Finance", method=args.get("method", "zscore"), threshold=float(args.get("threshold", 2.5)))
        return {"content": [{"type": "text", "text": str(res)}]}

    @tool("forecast_metric", "Forecast periods ahead for a named metric.", {"metric_name": str, "periods": int})
    async def _forecast(args):
        res = await forecast_metric(metric_name=args.get("metric_name") or "Revenue", periods=int(args.get("periods", 6)))
        return {"content": [{"type": "text", "text": str(res)}]}

    @tool("list_available_metrics", "List metrics, categories, and periods.", {"domain": str})
    async def _list_metrics(args):
        res = await list_available_metrics(domain=args.get("domain") or None)
        return {"content": [{"type": "text", "text": str(res)}]}

    @tool("get_executive_summary", "Synthesize health, KPIs, and anomalies into a one-shot executive summary.", {})
    async def _exec_summary(args):
        res = await get_executive_summary()
        return {"content": [{"type": "text", "text": str(res)}]}


async def main() -> None:
    if not _SDK:
        print("claude_agent_sdk not installed. pip install claude-agent-sdk "
              "(and `npm i -g @anthropic-ai/claude-code`).")
        return

    server = create_sdk_mcp_server(name="agentkit", version="1.0.0", tools=[_health, _kpis, _anomalies, _forecast, _list_metrics, _exec_summary])
    options = ClaudeAgentOptions(
        mcp_servers={"agentkit": server},
        allowed_tools=[
            "mcp__agentkit__get_company_health", 
            "mcp__agentkit__query_kpis",
            "mcp__agentkit__detect_kpi_anomalies",
            "mcp__agentkit__forecast_metric",
            "mcp__agentkit__list_available_metrics",
            "mcp__agentkit__get_executive_summary"
        ],
        model=os.getenv("LLM_VISION_PREMIUM", "claude-sonnet-4-6"),
    )
    async for message in query(
        prompt="Summarize our company's health and the top Finance metrics to watch.",
        options=options,
    ):
        print(message)


if __name__ == "__main__":
    asyncio.run(main())
