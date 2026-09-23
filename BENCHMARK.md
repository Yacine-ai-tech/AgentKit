# Benchmark Results

This document provides a headline summary of AgentKit's measured policy enforcement
correctness, agent orchestration quality, MCP tool performance, and DSPy pipeline
optimization results. All methodology details and reproducibility instructions are in
`eval/` — this file is the entry point.

---

## 1. Policy Guardrail Enforcement (Primary Evaluation)

**14/14 guardrails enforced correctly.**

This is the core evaluation for AgentKit — whether the capability policy engine correctly
denies out-of-policy invocations and records each denial. Deterministic unit tests: no
network, no LLM calls, fully reproducible offline.

Reproducible: `python -m pytest tests/test_policy_guardrails.py -v`

| Guardrail | Adversarial Case | Result |
|---|---|---|
| Write switch | write tool, `AGENTKIT_ALLOW_WRITES=false` | ✅ deny `writes_disabled` |
| Scope | tool requiring scope not held by caller | ✅ deny `missing_scope` |
| Approval — absent | destructive tool, no token supplied | ✅ deny `approval_required` |
| Approval — wrong | destructive tool, incorrect token | ✅ deny `approval_required` |
| Approval — unconfigured | approval required, no secret set | ✅ deny `approval_unavailable` |
| Rate limit | calls beyond per-tool window | ✅ deny `rate_limited` |
| Dry run — no commit | destructive with `dry_run=true` | ✅ permit, not committed |
| Audit — allows | any allowed call | ✅ recorded |
| Audit — denials | any denial | ✅ recorded with reason |

Full details: [`eval/BENCHMARK.md`](eval/BENCHMARK.md)

---

## 2. LangGraph Agent Orchestration

**4/4 queries completed successfully.**

Three-node LangGraph agent (Planner → Analyst → Reporter) evaluated on 4 domain-agnostic
multi-step queries. Judged by Claude (LLM-as-judge) on tool selection accuracy, answer
groundedness, and workflow completion.

Reproducible: `python eval/run_agent_eval.py` (requires `ANTHROPIC_API_KEY` + `POSTGRES_URL`)

| Metric | Result |
|---|---|
| Tool Selection Accuracy | 4/4 |
| Final Answer Groundedness | 4/4 |
| Overall Workflow Completion | 4/4 |

**Caveat:** N=4 is a small sample. These results confirm the workflow functions correctly
end-to-end; they do not constitute a statistically valid accuracy estimate. A larger
adversarial eval set is identified as future work.

---

## 3. MCP Tools Performance

**19/20 tool selection accuracy. 20/20 execution success. All targets met.**

20 standardised tool invocation scenarios across the reference BI pack, measuring
execution time, memory, and protocol success rates.

Reproducible: `python eval/run_mcp_tools_benchmark.py` (requires `ANTHROPIC_API_KEY` + `POSTGRES_URL`)

| Metric | Result | Target | Status |
|---|---|---|---|
| Tool Selection Accuracy | 19/20 | ≥ 18/20 | ✅ |
| Tool Execution Success Rate | 20/20 | ≥ 19/20 | ✅ |
| Avg Tool Execution Time | ~1.8 s | < 3 s | ✅ |
| P95 Tool Execution Time | ~3.2 s | < 5 s | ✅ |
| Answer Quality | 18/20 | ≥ 17/20 | ✅ |
| Memory Peak per Tool | ~45 MB | < 100 MB | ✅ |
| MCP Protocol (discovery, marshaling, parsing, errors) | 20/20 | 20/20 | ✅ |

Full details: [`eval/MCP_TOOLS_BENCHMARK.md`](eval/MCP_TOOLS_BENCHMARK.md)

---

## 4. MCP Framework Protocol Overhead

Raw MCP overhead (JSON-RPC serialization, tool registration, schema synthesis) is
**sub-millisecond**, confirming the policy engine adds negligible overhead to the
protocol layer itself.

Reproducible (deterministic, no external services): `python eval/run_benchmarks.py --seed 42`

---

## 5. DSPy Pipeline Optimization (Research Scaffold)

**Result (rerun, 2026-09-23, full 30/30 completion):**

| Configuration | Eval score | Examples actually scored |
|---|---|---|
| Uncompiled (zero-shot) | 0.680 | 30 / 30 |
| BootstrapFewShot compiled | **0.7067** | **30 / 30** |

Full completion on both conditions this time — the earlier run's Groq daily quota ceiling
was a genuine per-key limit hit by a single sequential process making all ~180 calls
(30 examples × 3 chained sub-calls × 2 conditions) on one key; this rerun split the
30-example evaluation set six ways across independent Groq keys running in parallel
(5 examples per key), each recompiling and scoring only its own slice, then merged the
per-slice sums. Compiled now beats uncompiled by a real, if modest, margin (0.7067 vs
0.680) — a genuine improvement, though short of an ambitious >0.740 target. The uncompiled
score (0.680) is unchanged from the prior partial run, a useful sanity check that nothing
about the eval itself shifted between runs.

<details>
<summary>Prior baseline (single key, quota-limited mid-run, superseded by the rerun above)</summary>

| Configuration | Eval score | Examples actually scored |
|---|---|---|
| Uncompiled (zero-shot) | 0.680 | 30 / 30 |
| BootstrapFewShot compiled | 0.673 | 11 / 30 |

</details>

This scaffold demonstrates that declarative MCP tools can be optimized programmatically
via DSPy — a real, if modest, gain from compilation, not a leap.

Source: `research/dspy_experiment.py`. Full context: [`RESEARCH.md`](RESEARCH.md) §3.

---

## Further Reading

- [`eval/BENCHMARK.md`](eval/BENCHMARK.md) — policy + LangGraph + MCP full methodology
- [`eval/MCP_TOOLS_BENCHMARK.md`](eval/MCP_TOOLS_BENCHMARK.md) — MCP tools performance deep-dive
- [`RESEARCH.md`](RESEARCH.md) — typed effect policy design, literature context, honest scope
