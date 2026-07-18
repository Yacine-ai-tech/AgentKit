# AgentKit — MCP Server for Business Intelligence Agents

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)


[![CI](https://github.com/Yacine-ai-tech/AgentKit/actions/workflows/ci.yml/badge.svg)](https://github.com/Yacine-ai-tech/AgentKit/actions/workflows/ci.yml) [![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](LICENSE)

Expose enterprise KPIs, health scores, forecasting, and anomaly detection as
tools, resources, and prompt templates that any MCP-compatible agent (Claude
Desktop, Cursor, LangGraph, Claude Agent SDK, CrewAI) can use.
> 🔗 **Live MCP server (SSE):** https://agentkit.ysiddo-ai-projects.app/sse — connect from Claude Desktop
> via `mcp-remote` (see [claude_desktop_config.example.json](claude_desktop_config.example.json)). On-demand backend (first call ~30–60 s).
> Self-hosting: see [SELF_HOSTING.md](SELF_HOSTING.md).

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

## ⚖️ License & Enterprise Use (Dual-License)

This project is open-source under the **AGPL-3.0 License**. It is completely free for researchers, students, and open-source hobbyists.

> **Commercial Use:** The AGPLv3 license requires that any proprietary network service (SaaS, internal corporate tools) that uses or modifies this code must also open-source its entire backend. 
> 
> If you wish to use this framework in a closed-source commercial environment, or require **Enterprise features** (SSO, Active Directory, Custom VPC Deployment, Strict RBAC), you must obtain a **Commercial License**. 
> Please reach out to discuss commercial licensing and integration consulting.

## 📡 Anonymous Telemetry
This project collects anonymous, GDPR-compliant startup pings to help the author understand usage volume and prioritize development. 
* **What is collected:** Only the project name and a "startup" event timestamp. No PII, no API keys, no user data.
* **How to disable:** We respect your privacy. To opt-out, simply set `TELEMETRY_OPT_OUT=true` in your `.env` file.


<!-- Scarf Analytics Pixel -->
<img referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=5f5bf922-eb01-4e07-a540-23c68e6752cc" />

## Licensing
This project is licensed under the [AGPL-3.0 License](LICENSE).

**Commercial Use:** If you wish to use this software commercially without releasing your own source code, please see [COMMERCIAL.md](COMMERCIAL.md) to obtain a commercial license.

**Telemetry:** See [TELEMETRY.md](TELEMETRY.md) for our privacy-first data practices.
