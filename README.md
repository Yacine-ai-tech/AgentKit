# AgentKit — MCP Server for Business Intelligence Agents

[![CI](https://github.com/Yacine-ai-tech/AgentKit/actions/workflows/ci.yml/badge.svg)](https://github.com/Yacine-ai-tech/AgentKit/actions/workflows/ci.yml)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](LICENSE)

Expose enterprise KPIs, health scores, forecasting, and anomaly detection as
tools, resources, and prompt templates that any MCP-compatible agent (Claude
Desktop, Cursor, LangGraph, Claude Agent SDK, CrewAI) can use.

> 🔗 **Live MCP server (dashboard):** https://agentkit.ysiddo-ai-projects.app — connect from Claude Desktop
> via `mcp-remote` (see [claude_desktop_config.example.json](claude_desktop_config.example.json)). On-demand backend (first call ~30–60 s).
> Self-hosting: see [SELF_HOSTING.md](SELF_HOSTING.md).


## What It Does

- **6 MCP Tools**: `query_kpis`, `get_company_health`, `detect_kpi_anomalies`, `forecast_metric`, `list_available_metrics`, `get_executive_summary`
- **6 MCP Resources**: `kpi://Finance/latest` and similar for Growth, Operations, People, ESG, IT_Ops
- **1 Reusable Prompt**: `monthly_executive_briefing`
- **LangGraph 3-agent workflow** in `workflow.py` (Planner → Analyst → Reporter)
- **Claude Agent SDK demo** in `demos/claude_agent_sdk_demo.py`
- **CrewAI demo** in `demos/crewai_demo.py`
- **DSPy research scaffold** in `research/dspy_experiment.py`
- **34 tests** across smoke, API, integration, and LangGraph workflow

## PyPI Package

```bash
pip install agentkit-mcp   # v0.1.4
agentkit-mcp               # CLI entrypoint
```

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
        "ANTHROPIC_API_KEY": "sk-ant-...",
        "GROQ_API_KEY": "gsk_...",
        "OPENAI_API_KEY": "sk-...",
        "LLM_DEFAULT": "groq/llama-3.3-70b-versatile",
        "LLM_REASONING": "anthropic/claude-sonnet-4-6",
        "LLM_JUDGE": "anthropic/claude-haiku-4-5",
        "LLM_LOCAL": "ollama/llama3.3",
        "LOG_LEVEL": "DEBUG",
        "TELEMETRY_OPT_OUT": "true"
      }
    }
  }
}
```

### Leveraging Full Platform Capabilities
AgentKit is highly configurable. Make sure you are not underestimating its capabilities by omitting key environment variables:
- **LLM Routing/Overrides**: Use `LLM_DEFAULT`, `LLM_REASONING`, `LLM_JUDGE`, and `LLM_LOCAL` to precisely route distinct tasks to the most suitable models, ensuring you get the best balance of speed and cost.
- **Provider Support**: In addition to Anthropic and Groq, OpenAI (`OPENAI_API_KEY`) and Ollama are natively supported.
- **Diagnostics**: You can adjust `LOG_LEVEL` to `DEBUG` to gain deeper insights into the orchestration engine.
- **Telemetry**: The platform automatically sends anonymous telemetry, but you have the flexibility to disable it via `TELEMETRY_OPT_OUT=true`.

Restart Claude Desktop, then ask:
- "What's our company health right now?"
- "Forecast revenue for the next 6 months."
- "Are there anomalies in the Finance KPIs?"

## LangGraph Workflow

```python
from agentkit_mcp.workflow import analyze
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

## Research Novelty & Scientific Contributions

AgentKit is both industry-proof and scientifically reproducible:
- **Standardized Model Context Protocol (MCP) Middleware**: Unified stdio and SSE transport for hot-swappable agent tools.
- **Zero-Latency Schema Validation**: Formal runtime schema type checking and injection safety bounds.
- **Multi-Agent Interoperability**: Tested and verified across **Claude Desktop**, **Cursor IDE**, and **Devin AI**.

For full theoretical formulation, math bounds, and citation details, see [RESEARCH.md](RESEARCH.md).

## Benchmark Replication Suite

Run the reproducible benchmark evaluation suites:
```bash
# Test MCP framework overhead
python3 eval/run_benchmarks.py --seed 42

# Test Agent Tool Selection & Quality
python3 eval/run_agent_eval.py

# Test Comprehensive MCP Tool Execution Metrics
python3 eval/run_mcp_tools_benchmark.py
```

## Integration Guides (Claude Desktop, Cursor, Devin)

- **Claude Desktop**: See [claude_desktop_config.example.json](claude_desktop_config.example.json) and [docs/INTEGRATION_GUIDE.md](docs/INTEGRATION_GUIDE.md)
- **Cursor IDE**: See [cursor_mcp.example.json](cursor_mcp.example.json)
- **Devin AI Agent**: See [devin_mcp.example.json](devin_mcp.example.json)

Automated client verification:
```bash
python3 tests/test_mcp_client.py
```

## License & Enterprise Use (Dual-License)

This project is open-source under the **AGPL-3.0 License**. It is completely free for researchers, students, and open-source hobbyists.
Commercial license: see [COMMERCIAL.md](COMMERCIAL.md).

