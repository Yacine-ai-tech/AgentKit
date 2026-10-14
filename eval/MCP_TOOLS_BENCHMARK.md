# AgentKit — MCP Tools Performance Benchmark

> Figures recorded: 2026-10. Document last reviewed: 2026-10-14.

A comprehensive benchmark of AgentKit's MCP (Model Context Protocol) tools performance, accuracy, and resource utilization, run against the real 3-agent LangGraph workflow (`POST /api/workflow/run`). Reproducible:
`python eval/run_mcp_tools_benchmark.py`

## Setup
- Test Suite: 12 standardized queries spanning 5 of the 10 seeded domains
- Tool Categories: Finance KPIs, People KPIs, Operations KPIs, Customer KPIs, Engineering KPIs, Forecasting, Anomalies
- Metrics: Domain-selection accuracy, execution time, memory usage, success rate
- Engine: Real 3-agent LangGraph workflow (Planner → Analyst → Reporter) via AgentKit's REST facade
- Database: PostgreSQL

## Results (real run, 2026-10-13, N=12)

| Metric | Result |
|--------|--------|
| **Tool/Domain Selection Accuracy** | **100.0%** |
| **Tool Execution Success Rate** | **100.0%** |
| **Avg Tool Execution Time** | **28.0s** |
| **P95 Tool Execution Time** | **49.5s** |
| **Report Generation Quality** | **100.0%** |
| **Benchmark-client memory delta (peak)** | **1MB** |

**Tool Breakdown:**

| Tool Category | Success Rate | Avg Time | Accuracy |
|---------------|--------------|----------|----------|
| Finance KPIs | 100% | 8.9s | 100% |
| Anomalies | 100% | 37.6s | 100% |
| People KPIs | 100% | 32.7s | 100% |
| Operations KPIs | 100% | 42.4s | 100% |
| Customer KPIs | 100% | 22.2s | 100% |
| Engineering KPIs | 100% | 21.6s | 100% |
| Forecasting | 100% | 42.3s | 100% |

Execution time covers the whole three-agent workflow (planner, analyst and reporter model calls in sequence), so it is dominated by LLM generation and varies with provider rate limits. The memory figure is the change in the benchmark client's own resident memory, not the server's. Tool selection means that the expected domain's data was retrieved by the analyst step.

## Earlier recorded runs

### 10-Domain Enterprise MCP Tool Selection (N=12)

| Metric | Result | Target |
|---|---|---|
| Tool Selection Accuracy | 12/12 (100%) | >= 11/12 |
| Tool Execution Success Rate | 12/12 (100%) | 100% |
| P95 Execution Latency (single tool call) | 1.12 s | < 2.0 s |
| Schema Validation Rate | 100% | 100% |

### General Tool Orchestration Suite (N=20)

| Metric | Result | Target |
|---|---|---|
| Tool Selection Accuracy | 19/20 (95.0%) | >= 18/20 |
| Execution Success Rate | 20/20 (100%) | 100% |
| Avg Tool Execution Time | ~1.8 s | < 3 s |
| P95 Execution Latency | 3.2 s | < 5.0 s |
| Answer Quality | 18/20 | >= 17/20 |
| Memory Peak per Tool | 45 MB | < 100 MB |
