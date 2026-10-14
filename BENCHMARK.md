# Benchmark Results

> Figures recorded: 2026-10. Document last reviewed: 2026-10-14.

This document summarizes AgentKit's measured policy-enforcement correctness, agent
orchestration quality, MCP tool performance, and DSPy pipeline optimization results. Full
methodology and reproduction instructions are in `eval/`.

---

## 1. Policy Guardrail Enforcement (Primary Evaluation)

**16/16 guardrail tests pass** (the earlier published run of this suite reported 14/14; two tests were added since).

This is AgentKit's core evaluation — whether the capability policy engine correctly denies
out-of-policy invocations and records each denial. The suite is fully deterministic: no
network access and no LLM calls.

Reproducible: `python -m pytest tests/test_policy_guardrails.py -v`

| Guardrail | Adversarial case | Result |
|---|---|---|
| Write switch | Write tool, `AGENTKIT_ALLOW_WRITES=false` | Deny (`writes_disabled`) |
| Scope | Tool requiring a scope the caller lacks | Deny (`missing_scope`) |
| Approval, absent | Destructive tool, no token supplied | Deny (`approval_required`) |
| Approval, incorrect | Destructive tool, wrong token | Deny (`approval_required`) |
| Approval, unconfigured | Approval required, no secret set | Deny (`approval_unavailable`) |
| Rate limit | Calls beyond the per-tool window | Deny (`rate_limited`) |
| Dry run | Destructive call with `dry_run=true` | Permit, not committed |
| Audit, allowed | Any allowed call | Recorded |
| Audit, denied | Any denial | Recorded with reason |

Full detail: [`eval/BENCHMARK.md`](eval/BENCHMARK.md)

---

## 2. LangGraph Agent Orchestration

**43/43 scenarios passed**, spanning all 10 KPI domains plus cross-domain queries.

The three-node LangGraph agent (Planner → Analyst → Reporter) is evaluated on a 43-scenario
suite (`eval/multi_domain_scenarios.json`, `eval/run_dspy_eval.py`) covering every KPI domain
(Finance, People, Operations, Customer, Engineering, Growth, Logistics, ESG, IT, Security) and
seven cross-domain queries, judged on tool-routing correctness and report content quality.
The analyst's tool routing is deterministic keyword matching, so this suite checks architectural
coverage across the 10 domains rather than model reasoning quality.

Reproducible: `python eval/run_dspy_eval.py` (requires `GROQ_API_KEY` or `ANTHROPIC_API_KEY` +
`POSTGRES_URL`)

| Metric | Result |
|---|---|
| Tool-routing coverage | **43/43 (100%)** |
| Overall pass (tool + keyword + report length) | **43/43 (100%)** |

| Domain | Pass |
|---|---|
| Finance | 5/5 |
| People | 4/4 |
| Operations | 4/4 |
| Customer | 4/4 |
| Engineering | 4/4 |
| Growth | 3/3 |
| Logistics | 3/3 |
| ESG | 3/3 |
| IT | 3/3 |
| Security | 3/3 |
| Cross-domain | 7/7 |

Every scenario passed on both tool routing and report-content quality across all 10 domains.

---

## 3. MCP Tools Performance

**12/12 (100%) tool-selection accuracy, 12/12 tool-execution success**, measured against the
live public deployment on 2026-10-13.

The scenario suite (`eval/run_mcp_tools_benchmark.py`) defines 12 standardized tool-invocation
scenarios across the reference business-intelligence pack (5 of the 10 domains plus forecasting
and anomalies), measuring execution time and success rate.

Reproducible: `python eval/run_mcp_tools_benchmark.py` (requires `GROQ_API_KEY` or
`ANTHROPIC_API_KEY` + `POSTGRES_URL`, and a running AgentKit instance at `AGENTKIT_URL`)

| Metric | Result | What it means |
|---|---|---|
| Tool Selection Accuracy | **12/12 (100%)** | Expected domain data retrieved |
| Tool Execution Success Rate | **12/12 (100%)** | No workflow errors |
| Avg. Tool Execution Time | 28.0 s | Full three-agent workflow (run of 2026-10-13); 26.87 s in the earlier run |
| P95 Tool Execution Time | 49.5 s | Slowest queries (run of 2026-10-13); 39.86 s in the earlier run |
| P95 single-tool call latency | 1.12 s | Direct tool execution without the three LLM calls (N=12) |
| Report Quality | **12/12 (100%)** | Expected content fields present |

All 12 business intelligence scenarios passed on both tool selection and execution correctness across all configured domain tools.

A second, general orchestration suite (N=20) recorded 19/20 tool selection (95.0%), 20/20 execution success, P95 3.2 s per tool call and a 45 MB peak per tool.

Full detail: [`eval/MCP_TOOLS_BENCHMARK.md`](eval/MCP_TOOLS_BENCHMARK.md)

---

## 4. MCP Framework Protocol Overhead

Raw MCP overhead (JSON-RPC serialization, tool registration, schema synthesis) is
sub-millisecond in `eval/run_benchmarks.py`. That script measures the protocol layer, not the
policy engine's own cost.

Reproducible (deterministic, no external services): `python eval/run_benchmarks.py --seed 42`

---

## 5. DSPy Pipeline Optimization (Research Scaffold)

**Compiled pipelines outperform the uncompiled baseline, N=30 held-out examples, full
completion on both conditions.**

`research/dspy_experiment.py` casts the Planner → Analyst → Reporter workflow as a DSPy
module and compares zero-shot performance against a `BootstrapFewShot`-compiled version, on a
held-out evaluation set of hand-authored business questions, distinct from the demonstration
pool used for compilation.

| Configuration | Eval score | Examples scored |
|---|---|---|
| Uncompiled (zero-shot) | 0.680 | 30 / 30 |
| BootstrapFewShot compiled | **0.7067** | 30 / 30 |

Compilation improves on the uncompiled baseline by a real, modest margin. This demonstrates
that declarative MCP tools can be optimized programmatically via DSPy — a genuine, if modest,
gain from compilation rather than a categorical improvement.

Source: `research/dspy_experiment.py`. Full context: [`RESEARCH.md`](RESEARCH.md) §3.

---

## Further Reading

- [`eval/BENCHMARK.md`](eval/BENCHMARK.md) — policy, LangGraph, and MCP full methodology
- [`eval/MCP_TOOLS_BENCHMARK.md`](eval/MCP_TOOLS_BENCHMARK.md) — MCP tools performance detail
- [`RESEARCH.md`](RESEARCH.md) — typed-effect policy design, literature context, and scope
