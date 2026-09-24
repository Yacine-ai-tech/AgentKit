# AgentKit — Research Notes

## Abstract

AgentKit is an open-source MCP (Model Context Protocol) server implementing a capability
policy engine for governed LLM tool execution. Its primary engineering contribution is the
enforcement of typed effect policies at the protocol layer — below the agent and independent
of prompt content — ensuring that the reachable action set is bounded by deployment
configuration regardless of what an LLM is persuaded to attempt. The system is demonstrated
across four agent frameworks (LangGraph, Claude Agent SDK, CrewAI, and raw MCP clients)
against a shared policy engine, and includes a DSPy-based research scaffold for automated
pipeline optimization.

---

## 1. Context and Motivation

### 1.1 The MCP Security Gap

The Model Context Protocol (MCP), introduced by Anthropic in late 2024, has become a de facto
standard for connecting LLM agents to external tools and data sources. By mid-2026, MCP has
seen rapid industry adoption across Claude Desktop, Cursor IDE, Devin AI, and dozens of
third-party integrations.

Its rapid adoption has outpaced its initial security model. Industry research and security
audits in 2025–2026 consistently identify the same class of vulnerability: agent tool servers
grant excessive, unconstrained permissions, relying on system-prompt instructions as the
primary access-control mechanism. This approach is architecturally unsound:

1. The system prompt is the primary channel an adversary influences — retrieved content, user
   text, and tool output all flow into the same context that carries the restrictions
   (indirect prompt injection).
2. Most MCP servers treat all callers equally: there is no per-caller authorization, no notion
   of effect severity, and no audit trail distinguishing allowed calls from denied ones.
3. Writes and destructive operations are either fully blocked or fully open, with no graduated,
   human-in-the-loop control layer.

Key references from 2025–2026 converge on the same recommendation: security must be managed at
the architecture level — deterministic validators, strict tool contracts, and an observability
layer — not as a post-hoc prompt guardrail (Coalition for Secure AI, 2026; "Securing the Model
Context Protocol," arXiv 2026; OWASP Agentic AI Top 10, 2026).

### 1.2 Related Work

**Prompt injection and tool authorization.**
- *ARGUS* (2025): context-aware provenance signals to selectively gate invariant checks on
  tool calls. Shares the motivation of reducing the trust surface; differs by relying on the
  LLM layer to reason about provenance rather than enforcing static policy below it.
- *Task Shield* (2025): verifies that every tool call directly serves the original user goal —
  orthogonal to effect-based policy, addressing goal alignment rather than capability scope.
- *TypePilot* (2025): strongly typed language (Scala) constraints restricting LLM-generated
  code execution. Shares a type-theoretic ancestry; AgentKit applies analogous ideas at the
  tool-server level rather than to code generation.
- Dual-LLM architectures (Perez & Ribeiro, 2022; various 2024–2025 refinements): a separate
  auditor or verifier LLM inspects tool calls before execution. AgentKit's approach is
  complementary — deterministic enforcement requires no second LLM call and is not bypassable
  by a sufficiently persuasive prompt.

**MCP-specific security.**
- Published MCP security audits (2025–2026) find thousands of internet-facing MCP servers
  lacking basic authentication. AgentKit ships with bearer auth on the SSE endpoint and a
  writes-disabled default.
- The MCP specification (v1.0, 2024, ongoing) is transport-agnostic and defines tools,
  resources, and prompts, but intentionally defers authorization policy to implementers.
  AgentKit occupies that gap.

**Multi-agent orchestration.**
- LangGraph (LangChain, 2024): stateful, graph-based agent orchestration. AgentKit's reference
  workflow is a three-node LangGraph DAG (Planner → Analyst → Reporter), a common hierarchical
  architecture for decomposition-plus-synthesis tasks.
- DSPy (Khattab et al., 2023; production-mature by 2025): declarative, optimizable LLM
  pipelines using signatures and bootstrap compilation. `research/dspy_experiment.py` casts
  the same workflow as a DSPy module and measures compiled versus uncompiled performance.

---

## 2. Engineering Contribution: Typed Effects and Capability Policy at the Protocol Boundary

### 2.1 Problem Statement

Once an LLM tool server can cause side effects, the prevailing control is instruction-level:
the agent is told which actions are permitted. That control is unsound under adversarial
input, because the prompt is precisely the channel an attacker influences.

### 2.2 Design

Effect authority is declared per tool and enforced in the tool server, below the agent, so
that the reachable action set is invariant to the model's reasoning and to prompt content.

Let $\mathcal{T}$ be the registered tools. Each $t \in \mathcal{T}$ carries a policy envelope
$\pi(t) = \langle e, S, \rho, \alpha \rangle$: effect class $e \in \{\textsf{read},
\textsf{write}, \textsf{destructive}\}$, required scopes $S$, rate limit $\rho$, and approval
requirement $\alpha$. For an invocation with granted scopes $G$, supplied approval token $k$,
and dry-run flag $d$, execution proceeds only if:

$$
\textsf{allow}(t) \;=\;
\underbrace{(e = \textsf{read} \;\lor\; W)}_{\text{writes enabled}} \;\land\;
\underbrace{(S \subseteq G)}_{\text{scope}} \;\land\;
\underbrace{(\lnot\alpha \lor d \lor k = k^{*})}_{\text{human approval}} \;\land\;
\underbrace{(c_t < \rho)}_{\text{rate}}
$$

where $W$ is the deployment-wide write switch (default false) and $k^{*}$ is an approval
secret held outside the agent's context. Each conjunct fails closed: absent configuration
denies rather than permits.

The critical property: $\textsf{allow}$ depends on no term the model controls. The model
chooses $t$ and its arguments; it cannot supply $W$, $G$, or $k^{*}$. The reachable effect set
is therefore bounded by deployment configuration regardless of what the model is persuaded to
attempt — a guarantee prompt-level guardrails cannot provide.

Because enforcement sits in the server rather than any client, the same bound holds across
heterogeneous agent frameworks; this repository demonstrates LangGraph, Claude Agent SDK,
CrewAI, and raw MCP clients against one policy engine.

### 2.3 Additional Properties

- **Declarative YAML tool packs.** Tools are defined in YAML over Postgres or HTTP, not
  hardcoded in Python. Parameters are always bound, never string-interpolated, so a
  model-supplied value cannot alter query structure; undeclared arguments are rejected before
  reaching the driver.
- **Dry-run mode.** Mutating tools preview against the real database inside a transaction that
  is always rolled back, returning the true affected-row count without committing.
- **Audit trail.** Every invocation is recorded — allowed and denied — with the deny reason,
  effect class, caller, and outcome. `GET /api/audit` exposes the trail; `AGENTKIT_AUDIT_LOG`
  writes it as JSON Lines.
- **Policy introspection.** `GET /api/policy` publishes the full capability envelope, so "what
  can this agent actually do?" is answered by reading one endpoint rather than auditing source.

### 2.4 Scope

This is not presented as a novel theoretical framework. Its individual components —
capability-based access control, typed effects, fail-closed defaults, human-in-the-loop
approval for destructive actions — are well-established security patterns, applied here to the
specific problem of LLM tool servers and the MCP protocol. The contribution is their
combination and implementation at the protocol boundary, demonstrated across multiple agent
frameworks with a reproducible refusal benchmark.

Documented limitations:
- Scopes are process-wide, not per-caller identity; multi-tenant deployments require a gateway
  per trust boundary.
- No output-content filtering and no prompt-injection detection — the guardrails bound what an
  injection can cause, a different and more defensible property than detecting the injection
  itself.
- The approval-token mechanism is a simple shared-secret human-in-the-loop control; more
  sophisticated approval workflows (for example, per-action cryptographic receipts) are future
  work.

---

## 3. DSPy Research Scaffold

`research/dspy_experiment.py` frames the Planner → Analyst → Reporter pipeline as a DSPy
module with three signatures, comparing compiled (`BootstrapFewShot`) against uncompiled
performance. Eight hand-authored business questions serve only as the candidate-demonstration
pool for compilation; 30 further questions are held out entirely from compilation and used
only to score the two configurations, so the comparison reflects generalization rather than
memorized demonstrations.

| Configuration | Eval score | Examples scored |
|---|---|---|
| Uncompiled (zero-shot) | 0.680 | 30 / 30 |
| BootstrapFewShot compiled | **0.7067** | 30 / 30 |

Compilation improves on the uncompiled baseline by a real, modest margin, demonstrating that
declarative MCP tools can be optimized programmatically — a composability property that is
non-trivial when tool calls involve real database queries. Full detail:
[`BENCHMARK.md`](BENCHMARK.md#5-dspy-pipeline-optimization-research-scaffold).

---

## 4. Evaluation Protocol

### 4.1 Refusal Benchmark (Primary Evaluation)

The core evaluation is correct refusal under adversarial configuration, not task success: does
the server deny out-of-policy invocations, and is the denial recorded?

| Guardrail | Adversarial case | Required outcome |
|---|---|---|
| Write switch | Mutating tool, writes disabled | Deny (`writes_disabled`) |
| Scope | Tool requiring a scope the caller lacks | Deny (`missing_scope`) |
| Approval | Destructive tool, absent token | Deny (`approval_required`) |
| Approval config | Approval required, no secret set | Deny (`approval_unavailable`) |
| Rate | Calls beyond $\rho$ in the window | Deny (`rate_limited`) |
| Dry run | Destructive call with `dry_run=true` | Permit, no commit |
| Audit | Any denial | Recorded with reason |

**Result: 14/14 guardrails enforced correctly.** Reproducible via
`python -m pytest tests/test_policy_guardrails.py -v`. This suite is fully deterministic — no
network access, no LLM calls.

### 4.2 Agent Orchestration (LangGraph Workflow)

The LangGraph agent is evaluated on 43 scenarios spanning all 10 KPI domains plus
cross-domain queries requiring multi-step tool coordination, scored on tool-routing
correctness and report content quality.

**Result: 43/43 scenarios passed.** See [`BENCHMARK.md`](BENCHMARK.md#2-langgraph-agent-orchestration)
for full methodology.

### 4.3 MCP Tools Performance

12 standardized tool-invocation scenarios across the reference business-intelligence pack,
measuring execution time, memory, and protocol-layer success rate. See
[`eval/MCP_TOOLS_BENCHMARK.md`](eval/MCP_TOOLS_BENCHMARK.md).

**Result: 11/12 execution success, 11/12 tool-selection accuracy.**

---

## 5. Reproducibility

All evaluations are reproducible locally:

```bash
python -m pytest tests/test_policy_guardrails.py -v   # refusal benchmark — no network needed
python eval/run_dspy_eval.py                           # requires ANTHROPIC_API_KEY/GROQ_API_KEY + POSTGRES_URL
python eval/run_mcp_tools_benchmark.py                 # requires the same
python eval/run_benchmarks.py --seed 42                # MCP overhead — deterministic
```

The refusal benchmark requires no external services or API keys. The agent-orchestration and
MCP-tools benchmarks require a live Postgres database and an LLM provider key.

---

## 6. Future Directions

- **Per-caller identity and fine-grained authorization.** Current scopes are process-wide. A
  natural extension is per-request identity propagation — for example, OAuth 2.1 token
  introspection at the MCP layer — enabling multi-tenant deployments with distinct capability
  envelopes per caller.
- **Formal verification of the policy engine.** The $\textsf{allow}$ predicate is amenable to
  lightweight formal methods (Alloy, or a Datalog encoding) to mechanically verify that no
  combination of inputs bypasses a configured guardrail.
- **Adversarial evaluation at scale.** The current refusal benchmark covers 14 hand-crafted
  cases. A statistically valid adversarial dataset would require hundreds of examples,
  including automated red-teaming via an adversarial LLM generating injection attempts.
- **A larger DSPy evaluation set.** Scaling the held-out set beyond N=30 would tighten the
  compiled-versus-uncompiled comparison further.
- **Cross-framework policy parity.** Verifying that policy enforcement is identical across
  LangGraph, Claude Agent SDK, CrewAI, and raw MCP clients under concurrent load.

---

## 7. Citation

```bibtex
@software{agentkit2026,
  author    = {Yacine Seybou Siddo},
  title     = {AgentKit: A Governed MCP Tool Server with Typed Effect Policy},
  year      = {2026},
  url       = {https://github.com/Yacine-ai-tech/AgentKit},
  note      = {Open-source, AGPL-3.0}
}
```
