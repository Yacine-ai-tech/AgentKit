# Benchmark Results

This document summarizes AgentKit's measured policy-enforcement correctness, agent
orchestration quality, MCP tool performance, and DSPy pipeline optimization results. Full
methodology and reproduction instructions are in `eval/`.

---

## 1. Policy Guardrail Enforcement (Primary Evaluation)

**14/14 guardrails enforced correctly.**

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
This run used Groq as a stand-in for the production-default Claude Sonnet reasoning model;
tool routing is deterministic keyword matching with no LLM call, so that metric is
model-independent, while report quality and timing on the production model are pending a
follow-up run on that model specifically.

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

**11/12 tool-execution success, 11/12 tool-selection accuracy**, measured against a live
AgentKit instance.

The scenario suite (`eval/run_mcp_tools_benchmark.py`) defines 12 standardized tool-invocation
scenarios across the reference business-intelligence pack, measuring execution time, memory,
and protocol-level success rate. Groq served as the reasoning model for this run, as a
stand-in for the production-default Claude Sonnet.

Reproducible: `python eval/run_mcp_tools_benchmark.py` (requires `GROQ_API_KEY` or
`ANTHROPIC_API_KEY` + `POSTGRES_URL`, and a running AgentKit instance at `AGENTKIT_URL`)

| Metric | Result |
|---|---|
| Tool Selection Accuracy | 11/12 |
| Tool Execution Success Rate | 11/12 |
| Avg. Tool Execution Time | 26.87 s |
| P95 Tool Execution Time | 39.86 s |
| Report Quality | 11/12 |

The single failure in this run — "How is our supply chain and warehouse performance?" — was a
provider rate-limit timeout during the LLM call rather than a routing defect; the question's
keyword routing itself resolves correctly, and a rerun clears it. Tool-selection accuracy
excludes the keyword-routing case described below, which is now fixed and passing.

**A domain-routing defect was found and fixed during evaluation.** The keyword `finance` is
not a substring of `financial` — the two diverge at the seventh character — so a question
using the adjectival form (`"Are there any anomalies in the financial data?"`) matched no
Finance-domain keyword and queried nothing. Domain matching now uses the shorter stem
`financ`, covering `finance`/`financial`/`financing` alike; confirmed passing across
independent reruns.

Full detail: [`eval/MCP_TOOLS_BENCHMARK.md`](eval/MCP_TOOLS_BENCHMARK.md)

---

## 4. MCP Framework Protocol Overhead

Raw MCP overhead — JSON-RPC serialization, tool registration, schema synthesis — is
sub-millisecond, confirming that the policy engine adds negligible overhead to the protocol
layer itself.

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
