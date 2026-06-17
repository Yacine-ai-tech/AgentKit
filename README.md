# AgentKit — MCP Server for Business Intelligence Agents

[![CI](https://github.com/Yacine-ai-tech/AgentKit/actions/workflows/ci.yml/badge.svg)](https://github.com/Yacine-ai-tech/AgentKit/actions/workflows/ci.yml) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Expose enterprise KPIs, health scores, forecasting, and anomaly detection as
tools, resources, and prompt templates that any MCP-compatible agent (Claude
Desktop, Cursor, LangGraph, Claude Agent SDK, CrewAI) can use.

## What It Does

- **6 MCP Tools**: `query_kpis`, `get_company_health`, `detect_kpi_anomalies`, `forecast_metric`, `list_available_metrics`, `get_executive_summary`
- **6 MCP Resources**: `kpi://Finance/latest` and similar for Growth, Operations, People, ESG, IT_Ops
- **1 Reusable Prompt**: `monthly_executive_briefing`
- **LangGraph 3-agent workflow** in `workflow.py`
- **Claude Agent SDK demo** in `demos/claude_agent_sdk_demo.py`
- **CrewAI demo** in `demos/crewai_demo.py`
- **DSPy research scaffold** in `research/dspy_experiment.py`

## Quick Start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill in keys + POSTGRES_URL
python mcp_server.py
```

## Claude Desktop Setup

Add to `~/.config/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "agentkit": {
      "command": "python",
      "args": ["/abs/path/to/agentkit/mcp_server.py"],
      "env": {
        "POSTGRES_URL": "postgresql://...",
        "ANTHROPIC_API_KEY": "sk-ant-..."
      }
    }
  }
}
```

Restart Claude Desktop, then ask:
- "What's our company health right now?"
- "Forecast revenue for the next 6 months."
- "Are there anomalies in the Finance KPIs?"

## LangGraph Workflow

```python
from workflow import analyze
result = analyze("What drove gross margin in Q1?")
print(result["report"])
```

## Architecture

```
        Claude Desktop / Cursor / LangGraph
                      │
                      ▼ MCP
              ┌──────────────────┐
              │  mcp_server.py   │
              │   6 tools        │
              │   6 resources    │
              │   1 prompt       │
              └────────┬─────────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
   pg_store      insights      forecasting
   (KPIs)        (health,      (LinearReg
                 anomalies)    + Monte Carlo)
```

## License

MIT
