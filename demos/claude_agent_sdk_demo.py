"""
AgentKit demo — orchestration via the Claude Agent SDK.

Requires `claude-agent-sdk` to be installed and ANTHROPIC_API_KEY set.
"""
from __future__ import annotations

import asyncio
import os

from core.logger import get_logger

log = get_logger(__name__)

try:
    from claude_agent_sdk import Agent, MCPServer  # type: ignore
    _SDK = True
except ImportError:
    _SDK = False
    log.warning("claude_agent_sdk not installed — demo unavailable")


async def main() -> None:
    if not _SDK:
        print("claude_agent_sdk not installed. pip install claude-agent-sdk")
        return

    mcp_server = MCPServer(command="python", args=["mcp_server.py"])
    agent = Agent(
        model="claude-sonnet-4-6",
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        mcp_servers=[mcp_server],
    )
    result = await agent.run("Summarize our company's health and forecast revenue for next quarter.")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
