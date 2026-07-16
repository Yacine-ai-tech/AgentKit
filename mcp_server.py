from agentkit_mcp.mcp_server import mcp, _serve_sse, log, _FASTMCP
import os
if __name__ == "__main__":
    if _FASTMCP:
        transport = os.getenv("MCP_TRANSPORT") or ("sse" if os.getenv("PORT") else "stdio")
        port = int(os.getenv("MCP_PORT") or os.getenv("PORT") or "8005")
        log.info(f"Starting AgentKit wrapper (transport={transport} port={port})...")
        if transport == "sse": _serve_sse(port)
        else: mcp.run()
