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

from core.logger import get_logger

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

from mcp_server import get_company_health, query_kpis  # noqa: E402


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


async def main() -> None:
    if not _SDK:
        print("claude_agent_sdk not installed. pip install claude-agent-sdk "
              "(and `npm i -g @anthropic-ai/claude-code`).")
        return

    server = create_sdk_mcp_server(name="agentkit", version="1.0.0", tools=[_health, _kpis])
    options = ClaudeAgentOptions(
        mcp_servers={"agentkit": server},
        allowed_tools=["mcp__agentkit__get_company_health", "mcp__agentkit__query_kpis"],
        model=os.getenv("LLM_VISION_PREMIUM", "claude-sonnet-4-6"),
    )
    async for message in query(
        prompt="Summarize our company's health and the top Finance metrics to watch.",
        options=options,
    ):
        print(message)


if __name__ == "__main__":
    asyncio.run(main())
