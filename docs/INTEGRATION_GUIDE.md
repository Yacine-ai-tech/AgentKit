# AgentKit MCP Integration Guide: Claude Desktop, Cursor, and Devin

AgentKit implements the standard **Model Context Protocol (MCP)** specification over both `stdio` (for local desktop apps and IDEs) and `sse` (for cloud-deployed agent runners).

---

## 1. Claude Desktop Integration

### Configuration Path
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

### Configuration Snippet
Add AgentKit to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "agentkit": {
      "command": "python",
      "args": [
        "-m",
        "agentkit_mcp.mcp_server"
      ],
      "env": {
        "PYTHONPATH": "/path/to/AgentKit/src",
        "POSTGRES_URL": "postgresql://user:password@localhost/neondb?sslmode=require"
      }
    }
  }
}
```

### Verified Tools Available in Claude Desktop
- `query_kpis`: Fetch business metrics filtered by domain and period.
- `get_company_health`: Compute composite health score (0-100) across growth, margins, and cash runway.
- `detect_kpi_anomalies`: Z-score anomaly detection over historical KPI timelines.
- `forecast_metric`: Monte-Carlo simulated financial forecasting with 95% confidence intervals.
- `list_available_metrics`: Metadata discovery tool for domains, metrics, and periods.
- `get_executive_summary`: Synthesizes health, metrics, and anomalies into an executive brief.

---

## 2. Cursor IDE Integration

### Setup Steps
1. Open Cursor **Settings** (`Cmd+,` or `Ctrl+,`).
2. Navigate to **Features** -> **MCP Servers** -> **Add New MCP Server**.
3. Set **Name**: `AgentKit`
4. Set **Type**: `stdio`
5. Set **Command**: `python -m agentkit_mcp.mcp_server`
6. Add environment variable `PYTHONPATH=/path/to/AgentKit/src`.

Alternatively, add `.cursor/mcp.json` to your workspace root:

```json
{
  "mcpServers": {
    "agentkit-cursor": {
      "command": "python",
      "args": ["-m", "agentkit_mcp.mcp_server"],
      "env": {
        "PYTHONPATH": "${workspaceFolder}/AgentKit/src",
        "MCP_TRANSPORT": "stdio"
      }
    }
  }
}
```

---

## 3. Devin AI Agent Integration

### Setup Steps
Devin supports MCP servers via standard `stdio` or HTTP/SSE endpoints.

#### Stdio Mode
Configure in `.devin/mcp.json` or Devin environment settings:
```json
{
  "mcpServers": {
    "agentkit-devin": {
      "command": "python",
      "args": ["-m", "agentkit_mcp.mcp_server"],
      "env": {
        "PYTHONPATH": "/workspace/AgentKit/src",
        "MCP_TRANSPORT": "stdio"
      }
    }
  }
}
```

#### SSE Remote Mode (Render Deployed)
If connecting to a deployed AgentKit instance on Render:
```json
{
  "mcpServers": {
    "agentkit-remote": {
      "url": "https://agentkit-backend.onrender.com/sse",
      "headers": {
        "Authorization": "Bearer YOUR_MCP_AUTH_TOKEN"
      }
    }
  }
}
```

---

## 4. Verification & Diagnostics

Run the automated AgentKit client verification script:
```bash
python AgentKit/tests/test_mcp_client.py
```
This tests:
1. JSON-RPC 2.0 stdio initialization
2. `tools/list` protocol inspection
3. Direct execution of `list_available_metrics`, `get_company_health`, and `get_executive_summary`
4. `resources/list` and `prompts/list` standard responses.
