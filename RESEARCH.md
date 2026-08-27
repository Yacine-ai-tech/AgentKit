# AgentKit — Research Notes

## Abstract

AgentKit is an open-source MCP (Model Context Protocol) server implementing a **capability policy engine** for governed LLM tool execution. Its primary engineering contribution is the enforcement of typed effect policies at the protocol layer — below the agent and independent of prompt content — ensuring that the reachable action set is bounded by deployment configuration regardless of what an LLM is persuaded to attempt. The system is demonstrated across four agent frameworks (LangGraph, Claude Agent SDK, CrewAI, and raw MCP clients) against a shared policy engine and includes a DSPy-based research scaffold for automated pipeline optimization.

---

## 1. Context and Motivation

### 1.1 The MCP Security Gap

The Model Context Protocol (MCP), introduced by Anthropic in late 2024, has become a de facto standard for connecting LLM agents to external tools and data sources. By mid-2026, MCP has seen rapid industry adoption across Claude Desktop, Cursor IDE, Devin AI, and dozens of third-party integrations.

However, its rapid adoption has outpaced initial security models. Industry research and security audits in 2025–2026 consistently identify the same class of vulnerability: **agent tool servers grant excessive, unconstrained permissions**, relying on system-prompt instructions as the primary access control mechanism. This approach is architecturally unsound because:

1. The system prompt is the primary channel an adversary influences — retrieved content, user text, and tool output all flow into the same context that carries the restrictions (indirect prompt injection).
2. Most MCP servers treat all callers equally: there is no per-caller authorization, no notion of effect severity, and no audit trail that distinguishes allowed calls from denied ones.
3. Writes and destructive operations are either fully blocked or fully open — there is no graduated, human-in-the-loop control layer.

Key references from 2025–2026 converge on the same recommendation: *security must be managed at the architecture level — deterministic validators, strict tool contracts, and an observability layer — not as a post-hoc prompt guardrail* (Coalition for Secure AI, 2026; "Securing the Model Context Protocol," arXiv 2026; OWASP Agentic AI Top 10, 2026).

### 1.2 Related Work

**Prompt injection and tool authorization:**
- *ARGUS* (2025): context-aware provenance signals to gate invariant checks on tool calls selectively. Shares the motivation of reducing the trust surface; differs in relying on the LLM layer to reason about provenance rather than enforcing static policy below it.
- *Task Shield* (2025): verifies that every tool call directly serves the original user goal. Orthogonal to effect-based policy; addresses goal alignment rather than capability scope.
- *TypePilot* (2025): strongly typed language (Scala) constraints to restrict LLM-generated code execution. Type-theoretic ancestry shared; AgentKit applies analogous ideas at the tool-server level rather than code generation.
- Dual-LLM architectures (Perez & Ribeiro 2022; various 2024–2025 refinements): a separate auditor or verifier LLM inspects tool calls before execution. AgentKit's approach is complementary — deterministic enforcement does not require a second LLM call and is not bypassable by a sufficiently persuasive prompt.

**MCP-specific security:**
- Published MCP security audits (2025–2026): thousands of internet-facing MCP servers lack basic authentication. AgentKit ships with bearer auth on the SSE endpoint and a writes-disabled default.
- MCP specification (v1.0, 2024; ongoing): the protocol is transport-agnostic and defines tools, resources, and prompts. It intentionally defers authorization policy to implementers. AgentKit occupies this gap.

**Multi-agent orchestration:**
- LangGraph (LangChain, 2024): stateful graph-based agent orchestration. AgentKit's reference workflow is a three-node LangGraph DAG (Planner → Analyst → Reporter), which is a common hierarchical architecture for decomposition + synthesis tasks.
- DSPy (Khattab et al., 2023; production-mature by 2025): declarative, optimizable LLM pipelines using signatures and bootstrap compilation. AgentKit's `research/dspy_experiment.py` casts the same workflow as a DSPy module and measures compiled vs. uncompiled performance.

---

## 2. Engineering Contribution: Typed Effects and Capability Policy at the Protocol Boundary

### 2.1 Problem Statement

Once an LLM tool server can cause side effects, the prevailing control is instruction-level: the agent is *told* which actions are permitted. That control is unsound under adversarial input because the prompt is precisely the channel an attacker influences.

### 2.2 Design

Effect authority is declared per tool and enforced in the tool server — below the agent — so that the reachable action set is invariant to the model's reasoning and to prompt content.

Let $\mathcal{T}$ be the registered tools. Each $t \in \mathcal{T}$ carries a policy envelope $\pi(t) = \langle e, S, \rho, \alpha \rangle$: effect class $e \in \{\textsf{read}, \textsf{write}, \textsf{destructive}\}$, required scopes $S$, rate limit $\rho$, approval requirement $\alpha$. For an invocation with granted scopes $G$, supplied approval token $k$, and dry-run flag $d$, execution proceeds only if:

$$
\textsf{allow}(t) \;=\;
\underbrace{(e = \textsf{read} \;\lor\; W)}_{\text{writes enabled}} \;\land\;
\underbrace{(S \subseteq G)}_{\text{scope}} \;\land\;
\underbrace{(\lnot\alpha \lor d \lor k = k^{*})}_{\text{human approval}} \;\land\;
\underbrace{(c_t < \rho)}_{\text{rate}}
$$

where $W$ is the deployment-wide write switch (default **false**) and $k^{*}$ is an approval secret held outside the agent's context. Each conjunct fails closed: absent configuration denies rather than permits.

The critical property: $\textsf{allow}$ depends on no term the model controls. The model chooses $t$ and its arguments; it cannot supply $W$, $G$, or $k^{*}$. Hence the reachable effect set is bounded by deployment configuration regardless of what the model is persuaded to attempt — the guarantee prompt-level guardrails cannot make.

Because enforcement is in the server rather than any client, the same bound holds across heterogeneous agent frameworks; this repository demonstrates LangGraph, Claude Agent SDK, CrewAI, and raw MCP clients against one policy engine.

### 2.3 Additional Properties

- **Declarative YAML toolpacks**: Tools are defined in YAML over Postgres or HTTP, not hardcoded in Python. Parameters are always bound, never string-interpolated — a model-supplied value cannot alter query structure. Undeclared arguments are rejected before reaching the driver.
- **Dry-run mode**: Mutating tools preview against the real database inside a rolled-back transaction, returning the true affected-row count without committing.
- **Audit trail**: Every invocation recorded — allowed and denied — with the deny reason, effect class, caller, and outcome. `GET /api/audit` exposes the trail; `AGENTKIT_AUDIT_LOG` writes it as JSON Lines.
- **Policy introspection**: `GET /api/policy` publishes the full capability envelope, so "what can this agent actually do?" is answered by reading one endpoint rather than auditing source.

### 2.4 Honest Scope

This is **not** claimed as a novel theoretical framework. The individual components — capability-based access control, typed effects, fail-closed defaults, HITL for destructive actions — are well-established security patterns applied to the specific problem of LLM tool servers and the MCP protocol. The contribution is their **combination and implementation at the protocol boundary**, demonstrated working across multiple agent frameworks, with a reproducible refusal benchmark.

Limitations explicitly documented:
- Scopes are process-wide (not per-caller identity). Multi-tenant deployments require a gateway per trust boundary.
- No output content filtering, and no prompt-injection *detection* (the guardrails bound what an injection can cause — a different, more defensible property).
- The approval token mechanism is simple shared-secret HITL; more sophisticated approval workflows (e.g., per-action cryptographic receipts) are future work.

---

## 3. DSPy Research Scaffold

`research/dspy_experiment.py` frames the Planner → Analyst → Reporter pipeline as a DSPy `Module` with three signatures and evaluates compiled (BootstrapFewShot) vs. uncompiled performance on a held-out set of real, hand-authored business questions — 8 used only as BootstrapFewShot's candidate-demonstration pool (`TRAINSET`), 30 held out entirely from compilation and used only to score the two configurations (`EVALSET`), so the reported comparison reflects generalization rather than memorized training demos.

**Findings, real run (N=30 held-out eval examples, up from an earlier N=4 pilot):**

| Configuration | Eval score | Examples actually scored |
|---|---|---|
| Uncompiled (zero-shot) | **0.680** | 30 / 30 |
| BootstrapFewShot compiled | **0.673** | **11 / 30** |

**Read this plainly, not as "compiled loses":** the two numbers are not a clean apples-to-apples
comparison. The uncompiled pass completed cleanly against the full 30-example eval set. The
compiled pass hit a real Groq daily token-quota ceiling (200,000 TPD on the key this project now
uses) partway through — BootstrapFewShot itself succeeded (2 full demonstration traces
bootstrapped from the 8-example training pool, confirmed in the run log), but only 11 of the 30
held-out eval examples got scored before the account's daily quota was exhausted for the day; the
remaining 19 were skipped (not scored as failures) once the rate limit hit. The 0.673 vs 0.680
gap is well within the noise you'd expect from an 11-example subset and cannot be read as "the
compiled program is worse" — there isn't enough compiled-side data yet to make that comparison
honestly. (One more reporting caveat: the run's own summary line labeled the compiled result
`bootstrapped_0_demos` because the code only inspects `compiled.planner.demos` for the winner
label, while the log shows the 2 real bootstrapped traces attached elsewhere in the pipeline —
noted here rather than silently trusted, since the label undercounts what the run actually
produced.)

**What this does and doesn't establish:** N=30 with full uncompiled coverage is a meaningfully
larger, more trustworthy result than the original N=4 pilot for the *uncompiled* baseline. The
*compiled* side still isn't at a comparable N — closing that gap needs either a second Groq key
with its own daily quota, or running the remaining ~19 eval examples on a later day once the
quota resets, then merging results the same way `eval/reaggregate_action_item_benchmark.py`
merges partial runs elsewhere in this workspace. Until then, this is a real, honestly-reported
partial result, not a publication-grade compiled-vs-uncompiled conclusion.

The implementation correctly wraps the AgentKit tool functions as DSPy-compatible modules, demonstrating that declarative MCP tools can be optimized programmatically — a composability property that is non-trivial when tool calls involve real database queries.

---

## 4. Evaluation Protocol

### 4.1 Refusal Benchmark (Primary Evaluation)

The core evaluation is **correct refusal under adversarial configuration** — not task success. The question is: does the server deny out-of-policy invocations, and is the denial recorded?

| Guardrail | Adversarial case | Required outcome |
|---|---|---|
| Write switch | mutating tool, writes disabled | deny (`writes_disabled`) |
| Scope | tool requiring scope caller lacks | deny (`missing_scope`) |
| Approval | destructive tool, absent token | deny (`approval_required`) |
| Approval config | approval required, no secret set | deny (`approval_unavailable`) |
| Rate | calls beyond $\rho$ in window | deny (`rate_limited`) |
| Dry run | destructive with `dry_run=true` | permit, **no commit** |
| Audit | any denial | recorded with reason |

**Result: 14/14 guardrails enforced correctly.** Reproducible via `python -m pytest tests/test_policy_guardrails.py -v`. This test suite is deterministic (no network, no LLM calls).

### 4.2 Agent Orchestration (LangGraph Workflow)

The LangGraph agent is evaluated on 4 domain-agnostic queries requiring multi-step tool coordination, judged by Claude as LLM-as-judge on tool selection accuracy, answer groundedness, and workflow completion.

**Result: 4/4 queries completed successfully.** See `eval/BENCHMARK.md` for the full methodology and caveats.

### 4.3 MCP Tools Performance

20 standardized tool invocation scenarios across the reference BI pack, measuring execution time, memory, and protocol-layer success rates. See `eval/MCP_TOOLS_BENCHMARK.md`.

---

## 5. Reproducibility

All evaluations are reproducible locally:

```bash
python -m pytest tests/test_policy_guardrails.py -v   # refusal benchmark — no network needed
python eval/run_agent_eval.py                          # requires ANTHROPIC_API_KEY + POSTGRES_URL
python eval/run_mcp_tools_benchmark.py                 # requires same
python eval/run_benchmarks.py --seed 42                # MCP overhead — deterministic
```

The refusal benchmark requires no external services and no API keys. Agent eval and MCP benchmarks require a live Postgres database and an LLM provider key.

---

## 6. Intended Future Directions

The current implementation identifies several open problems that merit further investigation:

- **Per-caller identity and fine-grained authorization**: Current scopes are process-wide. A natural extension is per-request identity propagation (e.g., OAuth 2.1 token introspection at the MCP layer) enabling multi-tenant deployments with different capability envelopes per caller.
- **Formal verification of the policy engine**: The $\textsf{allow}$ predicate is amenable to lightweight formal methods (e.g., Alloy or a Datalog encoding) to mechanically verify that no combination of inputs bypasses a configured guardrail.
- **Adversarial evaluation at scale**: The current refusal benchmark covers 14 hand-crafted cases. A statistically valid adversarial dataset would require hundreds of examples, including automated red-teaming via an adversarial LLM generating injection attempts.
- **Compiled pipeline evaluation**: Scaling the DSPy experiment to a proper held-out test set (N ≥ 50) to rigorously characterize compiled vs. uncompiled performance on the Planner-Analyst-Reporter workflow.
- **Cross-framework policy parity**: Verifying that policy enforcement is byte-identical across LangGraph, Claude Agent SDK, CrewAI, and raw MCP clients under concurrent load.

---

## 7. Citation

```bibtex
@software{agentkit2026,
  author    = {yacine-ai-tech},
  title     = {AgentKit: A Governed MCP Tool Server with Typed Effect Policy},
  year      = {2026},
  url       = {https://github.com/Yacine-ai-tech/AgentKit},
  note      = {Open-source, AGPL-3.0}
}
```
