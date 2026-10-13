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

**Summary: all 16 guardrail tests pass** (the table lists the nine behaviours they cover; the rest
check session isolation, argument redaction, wildcard scopes and effect validation).

This evaluation is fully reproducible with no external services.

---

## Benchmark 2 — LangGraph Agent Orchestration (`run_dspy_eval.py`)

**What it measures:** Does the three-node LangGraph agent (Planner → Analyst → Reporter) select
the right domain tools and produce a report with the expected content?

**Methodology:** 43 scenarios in `multi_domain_scenarios.json` covering all 10 KPI domains plus
seven cross-domain queries. A scenario passes when the expected tools were called, the expected
keywords appear and the report meets a minimum length. Tool routing in the analyst step is
deterministic keyword matching, so the suite checks coverage and wiring rather than model
reasoning quality.

```bash
python eval/run_dspy_eval.py
```

**Result:** 43/43 scenarios passed (last recorded run 2026-09-24; see the top-level
[`BENCHMARK.md`](../BENCHMARK.md) for the per-domain table). The earlier four-query smoke test in
`run_agent_eval.py` is kept as a quick end-to-end check and is not a statistical result.

---

## Benchmark 3 — MCP Tools Performance (`run_mcp_tools_benchmark.py`)

**What it measures:** End-to-end success and latency of the real workflow through AgentKit's REST
facade for 12 queries (5 of the 10 domains, plus forecasting and anomalies).

```bash
AGENTKIT_URL=https://<your-host> python eval/run_mcp_tools_benchmark.py --reset
```

**Result (2026-10-13, N=12, public deployment):** 12/12 selected the expected domain data and
completed; average 28.0 s and P95 49.5 s per query. The latency is three sequential LLM calls,
not protocol overhead. Per-category figures are in
[`MCP_TOOLS_BENCHMARK.md`](MCP_TOOLS_BENCHMARK.md).

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
