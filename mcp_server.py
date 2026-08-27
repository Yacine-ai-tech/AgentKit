import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from agentkit_mcp.mcp_server import _FASTMCP, _serve_sse, log, mcp  # noqa: E402
if __name__ == "__main__":
    if _FASTMCP:
        transport = os.getenv("MCP_TRANSPORT", "sse").lower()
        if transport == "stdio":
            log.info("Starting AgentKit MCP server (transport=stdio)...")
            mcp.run(transport="stdio", show_banner=False)
        else:
            port = int(os.getenv("MCP_PORT") or os.getenv("PORT") or "8005")
            log.info(
                f"Starting AgentKit wrapper (transport={transport} port={port})..."
            )
            _serve_sse(port)
