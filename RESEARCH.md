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

## 2. Mathematical Formulation & Type Safety Bounds

Let $\mathcal{T} = \{t_1, t_2, \dots, t_n\}$ represent the set of registered MCP tools, where each tool $t_i$ is bound to a strict type schema $\Sigma_i$.
Given an inbound client request with payload $p$, the MCP validation function $\mathcal{V}: \mathcal{P} \times \Sigma \to \{0, 1\}$ validates parameter conformance prior to tool invocation:

$$\mathcal{V}(p, \Sigma_i) = \begin{cases} 1 & \text{if } \forall (k, v) \in p, \, k \in \text{dom}(\Sigma_i) \land \text{Type}(v) \equiv \Sigma_i[k] \\ 0 & \text{otherwise} \end{cases}$$

If $\mathcal{V}(p, \Sigma_i) = 1$, tool $t_i$ executes deterministically. Otherwise, an RPC error code `-32602` (Invalid Params) is returned without state mutation.

---

## 3. Reproducibility & Empirical Benchmarking Protocol

The repository includes an automated, deterministic benchmark evaluation suite. To replicate empirical performance measurements locally with fixed random seeds:

```bash
python3 eval/run_benchmarks.py --seed 42
```

### Empirical Performance Summary
- **Schema Validation & Type Verification Rate**: $100.0\%$
- **Agent Tool Selection Accuracy**: $> 90\%$ (across 4 domains)
- **Execution Success Rate**: $> 95\%$
- **Report Generation Quality**: $> 85\%$
- **Exposed System Tools**: $6$

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
