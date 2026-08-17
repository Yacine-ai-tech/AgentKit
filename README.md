# AgentKit — A Governed MCP Tool Server

[![CI](https://github.com/Yacine-ai-tech/AgentKit/actions/workflows/ci.yml/badge.svg)](https://github.com/Yacine-ai-tech/AgentKit/actions/workflows/ci.yml)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](LICENSE)

An MCP server where **tools are declarative, effects are typed, and every action is
policy-gated and audited** — usable by any MCP client (Claude Desktop, Cursor,
LangGraph, Claude Agent SDK, CrewAI).

Three things distinguish it from a typical MCP server:

- **Declarative tools** — define tools in YAML over your own Postgres or HTTP API. No
  Python, no fork. ([docs/REUSE.md](docs/REUSE.md))
- **Real actions, not just reads** — tools declare an effect (`read` / `write` /
  `destructive`) and mutating tools genuinely mutate.
- **Guardrails that hold regardless of the prompt** — writes are off by default,
  destructive actions need a human-held approval token the model never sees, everything
  supports dry-run, and every call (allowed *and denied*) is audited.
  ([SECURITY.md](SECURITY.md#capability-guardrails))

The bundled business-intelligence tools below are the **reference pack** that
demonstrates all of this — not the limit of what the server does.

> 🔗 **Self-hosting:** see [SELF_HOSTING.md](SELF_HOSTING.md) to run your own instance.

## What It Does

**Reference BI pack (built in):**
- **6 MCP Tools**: `query_kpis`, `get_company_health`, `detect_kpi_anomalies`, `forecast_metric`, `list_available_metrics`, `get_executive_summary`
- **6 MCP Resources**: `kpi://Finance/latest` and similar for Growth, Operations, People, ESG, IT_Ops
- **1 Reusable Prompt**: `monthly_executive_briefing`

> These come from the **reference pack** — the core server ships with no hardcoded resources or prompts.
> You can add your own `@mcp.resource` / `@mcp.prompt` decorators, or load them from a tool pack.
> See [docs/REUSE.md](docs/REUSE.md#direction-3----adding-your-own-mcp-resources-and-prompts).


**Platform capabilities:**
- **Declarative tool packs** — add tools over your own Postgres/HTTP in YAML (`packs/`)
- **Typed effects + policy engine** — `GET /api/policy` publishes the capability envelope
- **Audit trail** — `GET /api/audit`, allowed and denied, with deny reasons
- **Multi-provider LLM routing incl. self-hosted** — `GET /api/llm-routing`
- **LangGraph 3-agent workflow** in `workflow.py` (Planner → Analyst → Reporter)
- **Claude Agent SDK demo** in `demos/claude_agent_sdk_demo.py`
- **CrewAI demo** in `demos/crewai_demo.py`
- **DSPy research scaffold** in `research/dspy_experiment.py`
- **34 tests** across smoke, API, integration, and LangGraph workflow

## PyPI Package

```bash
pip install agentkit-mcp   # v0.1.9
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
        "MCP_TRANSPORT": "stdio",
        "POSTGRES_URL": "postgresql://...",
        "LOG_LEVEL": "DEBUG",
        "TELEMETRY_OPT_OUT": "true"
      }
    }
  }
}
```

`MCP_TRANSPORT=stdio` is required here — without it `mcp_server.py` defaults to serving
over SSE (a network port) instead of talking JSON-RPC over the pipes Claude Desktop
spawns it with, and no tools will appear. Local stdio mode doesn't need
`MCP_AUTH_TOKEN` (the OS process boundary is the auth boundary); that variable only
matters for the SSE/network path.

### Multi-Provider LLM Routing
The 3-agent LangGraph workflow (`workflow.py`) and the demos/research scripts route
each role to its own model via [LiteLLM](https://docs.litellm.ai/), configured with
plain `provider/model` strings — no code changes to switch providers:
- `LLM_REASONING` — planner + reporter agents (defaults to `anthropic/claude-sonnet-4-6`)
- `LLM_DEFAULT` — the tool-calling analyst agent (defaults to `groq/openai/gpt-oss-120b`)
- `LLM_JUDGE` — used by the eval suite (defaults to `anthropic/claude-haiku-4-5`)
- `LLM_LOCAL` + `INFERENCE_MODE=local` — route to a local/self-hosted model (e.g. Ollama)
  instead of a hosted provider

Set the matching provider API key(s) (`GROQ_API_KEY`, `ANTHROPIC_API_KEY`,
`OPENAI_API_KEY`) for whichever models you reference above. See `.env.example`.
- **Diagnostics**: adjust `LOG_LEVEL` to `DEBUG` for verbose logs.
- **Telemetry**: an anonymous startup ping is sent by default; disable with `TELEMETRY_OPT_OUT=true`.

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

AgentKit is an industry-proof intelligence engine:
- **Standardized Model Context Protocol (MCP) Middleware**: Unified stdio and SSE transport for hot-swappable agent tools.
- **Capability Policy Engine**: Formal effect separation (read/write/destructive) and prompt-independent guardrails.
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
