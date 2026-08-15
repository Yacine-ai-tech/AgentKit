# AgentKit — Benchmark Suite

This directory contains reproducible benchmarks for AgentKit's performance, policy enforcement, and agent orchestration capabilities.

## Benchmark 1 — Policy Refusal Correctness (`test_policy_guardrails.py`)

**What it measures:** Does the capability policy engine correctly deny out-of-policy invocations, and does it record each denial?

**Methodology:** Deterministic unit tests — no network, no LLM calls, no external dependencies. Each test configures a specific adversarial condition and asserts the server denies the call with the correct reason code.

```bash
python -m pytest tests/test_policy_guardrails.py -v
```

| Guardrail | Adversarial Case | Result |
|---|---|---|
| Write switch | write tool, `AGENTKIT_ALLOW_WRITES=false` | deny `writes_disabled` ✅ |
| Scope | tool requiring scope not held by caller | deny `missing_scope` ✅ |
| Approval — absent | destructive tool, no token supplied | deny `approval_required` ✅ |
| Approval — wrong | destructive tool, incorrect token | deny `approval_required` ✅ |
| Approval — unconfigured | approval required, no secret set | deny `approval_unavailable` ✅ |
| Rate limit | calls beyond per-tool window | deny `rate_limited` ✅ |
| Dry run — no commit | destructive with `dry_run=true` | permit, not committed ✅ |
| Audit — allows | any allowed call | recorded ✅ |
| Audit — denials | any denial | recorded with reason ✅ |

**Summary: 14/14 guardrails enforced correctly.**

This evaluation is fully reproducible with no external services.

---

## Benchmark 2 — LangGraph Agent Orchestration (`run_agent_eval.py`)

**What it measures:** Does the three-node LangGraph agent (Planner → Analyst → Reporter) correctly select tools, execute them, and synthesize grounded answers?

**Methodology:**
- N=4 domain-agnostic queries requiring multi-step tool coordination
- Judge: Claude (LLM-as-judge) evaluating tool selection accuracy, answer groundedness, and workflow completion
- Queries span: data retrieval, anomaly analysis, forecasting, cross-metric synthesis

```bash
python eval/run_agent_eval.py
```

| Metric | Result | Notes |
|---|---|---|
| Tool Selection Accuracy | 4/4 | Correct tool invoked for each sub-task |
| Final Answer Groundedness | 4/4 | Answers traced to real tool output |
| Overall Workflow Completion | 4/4 | No agent loop failures or dead ends |

**Important caveat:** N=4 is a very small sample. These results confirm the workflow functions correctly end-to-end; they do not constitute a statistically valid accuracy estimate. A larger adversarial eval set is needed for that claim.

---

## Benchmark 3 — MCP Tools Performance (`run_mcp_tools_benchmark.py`)

**What it measures:** Protocol-layer reliability and latency for 20 standardized tool invocation scenarios across the reference BI pack.

**Setup:**
- N=20 invocation scenarios (reference pack: Finance, Operations, People KPIs + forecasting + anomalies)
- Measured: tool selection accuracy, execution time, memory, protocol success rates
- LLM: Claude 3.5 Sonnet (via Anthropic API)
- Database: PostgreSQL

```bash
python eval/run_mcp_tools_benchmark.py
```

| Metric | Result | Target | Status |
|---|---|---|---|
| **Tool Selection Accuracy** | 19/20 | ≥ 18/20 | ✅ |
| **Tool Execution Success Rate** | 20/20 | ≥ 19/20 | ✅ |
| **Avg Tool Execution Time** | ~1.8s | < 3s | ✅ |
| **P95 Tool Execution Time** | ~3.2s | < 5s | ✅ |
| **Answer Quality** | 18/20 | ≥ 17/20 | ✅ |
| **Memory Peak per Tool** | ~45MB | < 100MB | ✅ |
| **MCP protocol (discovery, marshaling, parsing, errors)** | 20/20 | 20/20 | ✅ |

*Execution time includes DB query + ML compute (insights/forecasting) + LiteLLM round trip. Pure MCP overhead (JSON-RPC serialization) is sub-millisecond.*

---

## Benchmark 4 — MCP Framework Overhead (`run_benchmarks.py`)

**What it measures:** Raw MCP protocol overhead independent of tool logic.

```bash
python eval/run_benchmarks.py --seed 42
```

Measures JSON-RPC serialization latency, tool registration cost at startup, and schema synthesis time for declarative YAML packs.

---

## Reproducing All Benchmarks

```bash
# 1. Policy refusal — no external services needed
python -m pytest tests/test_policy_guardrails.py -v

# 2. Agent orchestration — requires ANTHROPIC_API_KEY + POSTGRES_URL
python eval/run_agent_eval.py

# 3. MCP tools performance — requires same
python eval/run_mcp_tools_benchmark.py

# 4. MCP framework overhead — deterministic
python eval/run_benchmarks.py --seed 42
```

Set environment variables via `.env` (see `.env.example`).
