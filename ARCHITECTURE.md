# AgentKit Architecture

How AgentKit lets agents call business tools safely. This page complements
[`README.md`](README.md) (what it is and how to run it), [`RESEARCH.md`](RESEARCH.md) (the
reasoning behind the design) and [`BENCHMARK.md`](BENCHMARK.md) (measured results). An interactive
version is in the dashboard under **Architecture**.

## 1. System overview

```
 MCP clients (Claude Desktop, Cursor, Devin, custom agents)      HTTP callers · dashboard
        │ SSE / stdio                                                   │ REST facade
        └──────────────────────┬───────────────────────────────────────┘
                               ▼
                   policy engine: effects · scopes · approval · rate limit · dry-run
                               ▼  audit(pending)
              built-in KPI tools          declarative tool packs (YAML)
                               ▼  audit(outcome)
                         PostgreSQL / HTTP data sources
```

## 2. Components

| Component | Role |
|---|---|
| MCP server | six built-in read tools, resources and prompts over SSE or stdio |
| REST facade | the same tools as HTTP endpoints, plus policy, audit, packs and routing views |
| Policy engine | one enforcement point for every caller, independent of the agent framework |
| Audit trail | a record before execution and an outcome after, optionally to a JSONL file |
| Tool packs | tools defined in YAML over a Postgres or HTTP data source |
| LLM router | tiered model routing with a self-hosted tier and provider fallbacks |
| Workflow | LangGraph planner → analyst → reporter |
| Key pool | rotates provider keys and parks a rate-limited key until its retry window ends |

## 3. The call funnel

1. **Authenticate**: bearer token on the SSE endpoint, or the internal token on the REST facade.
2. **Decide** (fixed order): unknown tool, writes disabled, missing scope, destructive without
   approval, rate limit exceeded — otherwise allow; a dry run is allowed but simulated.
3. **Record**: write the decision before anything runs.
4. **Execute**: built-in tools read from the KPI store; pack tools run bound, never interpolated,
   SQL in a worker thread.
5. **Record the outcome** and return JSON. The facade maps denial to 403, bad input to 422 and
   execution failure to 502.

## 4. Capability policy

| Effect | Meaning | Gate |
|---|---|---|
| `read` | no side effects | always allowed (still audited) |
| `write` | creates or modifies state | `AGENTKIT_ALLOW_WRITES=true` and the tool's scope |
| `destructive` | irreversible or externally visible | the above plus an approval token held by a human |

A fresh install cannot mutate anything. The approval token is never given to the model, so an agent
can propose a destructive action and a human authorises that specific call.

## 5. Tool packs

A pack is a YAML file: name, data source (credentials by named environment variable), and tools with
typed parameters, effect, scopes and a query or statement. Parameters are bound by the database
driver; the agent only fills declared parameters. Adding a tool to a deployment means writing YAML.
Packs are loaded from `AGENTKIT_PACKS` (default: the bundled `packs/` directory).

## 6. Model routing

| Tier | Used for |
|---|---|
| default | the tool-calling analyst |
| reasoning | planner and report synthesis |
| judge | evaluation and scoring |
| local | any model on hardware you control (Ollama or an OpenAI-compatible server) |

`INFERENCE_MODE=local` sends every tier to the local model. `LLM_FALLBACK_TO_LOCAL=true` retries once
locally when a hosted call fails; it is opt-in because silently serving a weaker model is an
operator decision.

## 7. Design decisions

| Decision | Reason |
|---|---|
| Policy lives with the tool | LangGraph, CrewAI, the Claude Agent SDK and raw MCP clients all get identical enforcement |
| Fail closed | a default install exposed to the internet cannot mutate anything |
| Audit before execute | a crash still leaves the decision on record |
| Declared effects | capability is stated by the pack author, not inferred from SQL |
| Bound parameters | a model-supplied value cannot change query structure |
| Packs additive | no pack configured means the original six tools, unchanged |

## 8. Interfaces

| Route | Purpose |
|---|---|
| `GET /sse` (MCP), stdio | MCP transport |
| `GET /api/tools`, `/api/resources`, `/api/prompts/{name}` | discovery |
| `GET /api/kpis`, `/api/health-score`, `/api/anomalies`, `/api/forecast`, `/api/metrics`, `/api/summary` | built-in tools |
| `GET /api/policy`, `/api/audit`, `/api/llm-routing`, `/api/packs`, `/api/observability` | governance views |
| `POST /api/workflow/run` | run the planner → analyst → reporter workflow |
| `GET /health` | liveness |

## 9. Configuration

Everything is environment-driven; [`.env.example`](.env.example) lists every variable with its
purpose. Groups: database, MCP transport and auth, model tiers and local inference, capability
policy, packs, telemetry.

## 10. Privacy

The optional startup ping carries only service name, version and a random installation id; disable
it with `TELEMETRY_OPT_OUT=true` or `DO_NOT_TRACK=1`. Tool arguments, results and keys are not sent.
