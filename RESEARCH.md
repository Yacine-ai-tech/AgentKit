# AgentKit: Standardized Model Context Protocol (MCP) Middleware & Agent Tool Orchestration Framework

## Abstract
AgentKit provides a standardized Model Context Protocol (MCP) middleware layer for heterogeneous AI agent tool orchestration. Implemented over standard `stdio` and `sse` transports, AgentKit decouples agent tool definitions, type verification, and runtime execution. The framework enforces dynamic runtime schema validation to guarantee payload integrity and type safety across multi-client environments including Claude Desktop, Cursor IDE, Devin AI, and custom LLM backends.

---

## 1. System Architecture & Technical Specifications

AgentKit exposes a structured tool registry, resource endpoints, and prompt templates adhering to the MCP 1.0 specification.

```
+-------------------------------------------------------------------+
|               Agent Clients (Claude Desktop / Cursor / Devin)      |
+-------------------------------------------------------------------+
                                  |
                                  v  MCP Protocol (stdio / sse)
+-------------------------------------------------------------------+
|                     agentkit_mcp.mcp_server                       |
|  - FastMCP Server Container                                       |
|  - JSON-RPC 2.0 Transport Handlers                                |
+-------------------------------------------------------------------+
        |                         |                         |
        v                         v                         v
+---------------+       +------------------+       +------------------+
|  KPI Query    |       | Health Analytics |       |   Forecasting    |
| (query_kpis)  |       | (company_health) |       | (Monte Carlo CI) |
+---------------+       +------------------+       +------------------+
```

### Registered System Capabilities
- **6 MCP Tools**: `query_kpis`, `get_company_health`, `detect_kpi_anomalies`, `forecast_metric`, `list_available_metrics`, `get_executive_summary`.
- **6 MCP Resources**: `kpi://Finance/latest`, `kpi://Growth/latest`, `kpi://Operations/latest`, `kpi://People/latest`, `kpi://ESG/latest`, `kpi://IT_Ops/latest`.
- **1 Prompt Template**: `monthly_executive_briefing`.

---

## 2. Contribution: Typed Effects & Capability Policy At The Protocol Boundary

> **Scope note (honest framing).** Runtime schema validation of tool parameters is *not*
> a contribution of this project — it is standard behaviour of the MCP specification and
> its server implementations. An earlier revision of this document presented that as a
> formal result; it was a restatement of existing behaviour and has been removed. What
> follows is the narrower claim this codebase actually supports.

**Problem.** Once an LLM tool server can cause side effects, the prevailing control is
instruction-level: the agent is *told* which actions are permitted. That control is
unsound under adversarial input, because the prompt is precisely the channel an attacker
influences. Retrieved content, tool output, and user text all flow into the same context
that carries the restrictions.

**Claim.** Effect authority should be declared per tool and enforced in the tool server,
below the agent, so that the reachable action set is invariant to the model's reasoning
and to prompt content.

Let $\mathcal{T}$ be the registered tools. Each $t \in \mathcal{T}$ carries a policy
envelope $\pi(t) = \langle e, S, \rho, \alpha \rangle$: effect class
$e \in \{\textsf{read}, \textsf{write}, \textsf{destructive}\}$, required scopes $S$,
rate limit $\rho$, approval requirement $\alpha$. For an invocation with granted scopes
$G$, supplied approval token $k$, and dry-run flag $d$, execution proceeds only if

$$
\textsf{allow}(t) \;=\;
\underbrace{(e = \textsf{read} \;\lor\; W)}_{\text{writes enabled}} \;\land\;
\underbrace{(S \subseteq G)}_{\text{scope}} \;\land\;
\underbrace{(\lnot\alpha \lor d \lor k = k^{*})}_{\text{human approval}} \;\land\;
\underbrace{(c_t < \rho)}_{\text{rate}}
$$

where $W$ is the deployment-wide write switch (default **false**) and $k^{*}$ is an
approval secret held outside the agent's context. Each conjunct fails closed: absent
configuration denies rather than permits — notably, $\alpha \land k^{*} = \emptyset$
denies, so a misconfigured approval gate cannot silently open.

The property of interest is that $\textsf{allow}$ depends on no term the model controls.
The model chooses $t$ and its arguments; it cannot supply $W$, $G$, or $k^{*}$. Hence
the reachable effect set is bounded by deployment configuration regardless of what the
model is persuaded to attempt — the guarantee prompt-level guardrails cannot make.

Because enforcement is in the server rather than any client, the same bound holds across
heterogeneous agent frameworks; this repository exercises LangGraph, Claude Agent SDK,
CrewAI, and raw MCP clients against one policy engine.

### 2.1 Evaluation: refusal under adversarial request

The corresponding eval is not task success but **correct refusal**: for each guardrail,
does the server deny out-of-policy invocations, and is the denial recorded?

| Guardrail | Adversarial case | Required outcome |
|---|---|---|
| Write switch | mutating tool, `AGENTKIT_ALLOW_WRITES=false` | deny (`writes_disabled`) |
| Scope | tool requiring scope caller lacks | deny (`missing_scope`) |
| Approval | destructive tool, absent/incorrect token | deny (`approval_required`) |
| Approval config | approval required, no secret configured | deny (`approval_unavailable`) |
| Rate | calls beyond $\rho$ in window | deny (`rate_limited`) |
| Dry run | destructive with `dry_run` | permit, **no commit** |
| Audit | any denial | recorded with reason |

Implemented in `tests/test_policy_guardrails.py` and reproducible via
`python -m pytest tests/test_policy_guardrails.py -v`. Denials, not successes, are the
measured property.

**Limitations.** Scopes are process-wide rather than per-caller identity; multi-tenant
deployments need a gateway per trust boundary. The scheme bounds *effects*, not
*information disclosure* — a read tool exposed to a compromised agent still reads. No
claim is made about output filtering or about detecting prompt injection, only about
bounding what an injected instruction can ultimately cause.

---

## 3. Reproducibility & Empirical Benchmarking Protocol

The repository includes an automated, deterministic benchmark evaluation suite. To replicate empirical performance measurements locally with fixed random seeds:

```bash
python3 eval/run_benchmarks.py --seed 42          # MCP framework overhead
python3 eval/run_agent_eval.py                    # tool selection + groundedness (N=4)
python3 -m pytest tests/test_policy_guardrails.py # refusal benchmark (§2.1)
```

### Empirical summary

| Measure | Result | Basis |
|---|---|---|
| Guardrail refusal correctness | 14/14 | `tests/test_policy_guardrails.py`, deterministic, no network |
| Agent tool selection + groundedness | 4/4 | `eval/run_agent_eval.py`, LLM-judged, N=4 |
| Exposed tools | 6 built-in + N declarative | packs are deployment-configured |

**Read these numbers narrowly.** The refusal benchmark is deterministic and meaningful:
it is the claim of §2. The N=4 agent eval is a smoke-scale sanity check on a single
question set — it is not a generalisation claim, and the earlier presentation of
percentages such as "> 90% tool selection accuracy" and "> 85% report quality" implied a
sample size and rigour that do not exist here. They have been replaced with the actual
counts. Any published version of this work needs a substantially larger, adversarially
constructed eval set before quoting rates.

---

## 4. Technical Citation

```bibtex
@techreport{siddo2026agentkit,
  author      = {Yacine Seybou Siddo},
  title       = {AgentKit: Standardized Model Context Protocol Middleware and Agent Tool Orchestration Framework},
  institution = {GitHub Repository},
  year        = {2026},
  url         = {https://github.com/Yacine-ai-tech/AgentKit}
}
```
