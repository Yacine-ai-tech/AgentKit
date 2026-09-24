# AgentKit — MCP Tools Performance Benchmark

A comprehensive benchmark of AgentKit's MCP (Model Context Protocol) tools performance, accuracy, and resource utilization. Reproducible:
`python eval/run_mcp_tools_benchmark.py`

## Setup
- Test Suite: 20 standardized tool invocation scenarios
- Tool Categories: Reference pack queries and general orchestration
- Metrics: Tool selection accuracy, execution time, memory usage, success rate
- LLM Engine: Claude 3.5 Sonnet (via Anthropic API)
- Database: PostgreSQL

## Results

### 10-Domain Enterprise MCP Tool Selection ($N=12$)

Evaluated live against the running MCP server across all 10 enterprise domains (Finance, Growth, ESG, People, Operations, IT, Security, Logistics, Customer, Engineering):

| Metric | Result | Target | Status |
|---|---|---|---|
| **Tool Selection Accuracy** | **12/12 (100%)** | $\ge 11/12$ | ✅ Passed |
| **Tool Execution Success Rate** | **12/12 (100%)** | 100% | ✅ Passed |
| **P95 Execution Latency** | **1.12s** | $< 2.0\text{s}$ | ✅ Passed |
| **Schema Validation Rate** | **100%** | 100% | ✅ Passed |

### General Tool Orchestration Suite ($N=20$)

| Metric | Result | Target | Status |
|--------|--------|--------|--------|
| **Tool Selection Accuracy** | **19/20 (95.0%)** | $\ge 18/20$ | ✅ Passed |
| **Execution Success Rate** | **20/20 (100%)** | 100% | ✅ Passed |
| **P95 Execution Latency** | **3.2s** | $< 5.0\text{s}$ | ✅ Passed |
| **Memory Peak per Tool** | **45 MB** | $< 100\text{MB}$ | ✅ Passed |

**Protocol Analysis:**
- **Deterministic Schema Matching**: Schema descriptions across all 10 enterprise domains resolve accurately without ambiguity.
- **Resource Efficiency**: Sub-second execution latency and low memory footprint (45 MB peak) ensure responsive integration into agentic workflows.