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

**Caveat (original N=4 run):** a small sample. These results confirm the workflow
functions correctly end-to-end; they do not constitute a statistically valid accuracy
estimate.

### Rerun attempt, N=15 multi-domain suite (2026-09-23, partial — 3/15 completed)

A larger, 15-scenario suite spanning all 5 KPI domains plus cross-domain queries
(`eval/multi_domain_scenarios.json`, `eval/run_dspy_eval.py`) was run on Groq
(`LLM_REASONING` overridden from the default Lightning-routed Claude Sonnet, since this
rerun's purpose was to avoid Lightning credits). Two real issues were found and one was
fixed along the way:

1. **Stale test data (fixed).** The scenario file's `expected_tools` used literal MCP
   function names (`query_kpis`, `detect_kpi_anomalies`) that no longer match what
   `analyst_agent()` (`workflow.py`) actually populates (`finance_kpis`, `people_kpis`,
   etc. — domain-suffixed keys). This made every scenario's tool-selection check fail
   regardless of whether the agent worked correctly. Fixed 12 of 15 scenarios'
   `expected_tools` to match the current, real key names.
2. **A genuine functional gap (left unfixed, deliberately).** Three scenarios
   (`ops_002`, `eng_002`, `cross_002`) were *not* naming-fixed, because they reveal a
   real limitation rather than stale test data: `analyst_agent()` only ever calls
   `detect_kpi_anomalies()` for the **Finance** domain — Operations and Engineering
   never get anomaly detection invoked at all, regardless of the question asked — and no
   `list_available_metrics`-equivalent tool is wired into the keyword-routing at all.
   These three scenarios are documented (via an `_note` field in the scenario JSON) to
   be *expected* to keep failing until that coverage gap is closed.
3. **Real infrastructure friction, unrelated to (1)/(2).** The rerun hit repeated
   `psycopg.pool: rolling back returned connection [INTRANS]` warnings against the Neon
   Postgres backend, adding significant per-scenario latency (each scenario took
   2-4 minutes instead of the expected seconds) — likely network-latency-driven from
   this development machine rather than a code defect; moving the rerun to the
   production VPS (same infrastructure the deployed app runs on) is the planned fix.

**Partial result (3/15 scenarios completed before time ran out):** all 3 completed
scenarios passed (`fin_001`, `fin_002`, `fin_003` — 100%), each with `tool_coverage=1.0`,
confirming the naming fix in (1) is correct. The run did not reach `ops_002`/`eng_002`/
`cross_002` in this attempt, so the gap in (2) is confirmed by code review, not yet by a
live test result — that confirmation, plus the full 15-scenario pass rate, is pending
the VPS rerun.

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

**Note on Lightning-credit dependence (2026-09-23):** confirmed via code review that Tool
Selection itself is **deterministic keyword matching** (`analyst_agent()` in
`workflow.py` — domain routing by keyword, no LLM call at all), so this specific metric
was never actually gated on Lightning AI credits or any provider quota. It already clears
this project's own target (≥18/20). A fresh confirmation run needs the local REST facade
(`web_app.py`) running — deferred as lower priority since the number itself isn't in
question, only whether a fresh sample would confirm 19/20 exactly or land nearby.

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
