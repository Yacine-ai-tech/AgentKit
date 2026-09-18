import argparse
import asyncio
import json
import os
import time
from pathlib import Path
from typing import Dict, List, Tuple

import httpx
import psutil

# Base URL for AgentKit's REST facade (web_app.py), not the raw MCP server.
AGENTKIT_URL = os.environ.get("AGENTKIT_URL", "http://localhost:8005")

DEFAULT_CACHE_FILE = Path(__file__).resolve().parent / "cache" / "mcp_tools_benchmark_cache.jsonl"

# Test scenarios spanning all 5 real domain categories seeded in src/data/seed.py
# (Finance/People/Operations/Customer/Engineering) plus forecasting/anomalies.
# expected_tools checks against the raw_data dict keys analyst_agent() populates
# in workflow.py — NOT literal MCP tool function names (query_kpis etc. are
# reused generically across domains via a `domain=` parameter, so tool selection
# here means "which domain(s) got queried", not "which Python function ran").
TEST_SCENARIOS = [
    {
        "query": "What are the current revenue trends?",
        "category": "Finance KPIs",
        "expected_tools": ["finance_kpis"],
        "expected_fields": ["revenue", "growth", "trend"],
    },
    {
        "query": "What is the current profit margin?",
        "category": "Finance KPIs",
        "expected_tools": ["finance_kpis"],
        "expected_fields": ["profit", "margin", "ratio"],
    },
    {
        "query": "Are there any anomalies in the financial data?",
        "category": "Anomalies",
        "expected_tools": ["finance_anomalies"],
        "expected_fields": ["anomaly", "outlier", "deviation"],
    },
    {
        "query": "Show me the headcount statistics",
        "category": "People KPIs",
        "expected_tools": ["people_kpis"],
        "expected_fields": ["headcount", "employees", "staff"],
    },
    {
        "query": "Show employee turnover and retention metrics",
        "category": "People KPIs",
        "expected_tools": ["people_kpis"],
        "expected_fields": ["turnover", "retention", "churn"],
    },
    {
        "query": "How is our supply chain and warehouse performance?",
        "category": "Operations KPIs",
        "expected_tools": ["operations_kpis"],
        "expected_fields": ["operations", "supply", "warehouse", "defect"],
    },
    {
        "query": "What is our defect rate and logistics efficiency?",
        "category": "Operations KPIs",
        "expected_tools": ["operations_kpis"],
        "expected_fields": ["defect", "logistics", "operations"],
    },
    {
        "query": "What is our customer churn rate and NPS score?",
        "category": "Customer KPIs",
        "expected_tools": ["customer_kpis"],
        "expected_fields": ["churn", "nps", "customer"],
    },
    {
        "query": "What is our customer lifetime value and support volume?",
        "category": "Customer KPIs",
        "expected_tools": ["customer_kpis"],
        "expected_fields": ["ltv", "customer", "support"],
    },
    {
        "query": "How is engineering deploy frequency and sprint velocity trending?",
        "category": "Engineering KPIs",
        "expected_tools": ["engineering_kpis"],
        "expected_fields": ["deploy", "sprint", "velocity", "engineering"],
    },
    {
        "query": "What is our MTTR and incident count this quarter?",
        "category": "Engineering KPIs",
        "expected_tools": ["engineering_kpis"],
        "expected_fields": ["mttr", "incident", "engineering"],
    },
    {
        "query": "Forecast the revenue for next quarter",
        "category": "Forecasting",
        "expected_tools": ["forecast_revenue"],
        "expected_fields": ["forecast", "prediction", "projected"],
    },
]


class MCPToolsBenchmark:
    def __init__(self, cache_file: Path = DEFAULT_CACHE_FILE):
        self.results = {
            "total_tests": 0,
            "successful": 0,
            "failed": 0,
            "tool_selection_correct": 0,
            "execution_times": [],
            "memory_samples": [],
            "report_quality": 0,
            "category_results": {},
        }
        self.process = psutil.Process(os.getpid())
        self.cache_file = cache_file
        self.cache: Dict[str, Dict] = {}
        if self.cache_file.exists():
            with open(self.cache_file) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    row = json.loads(line)
                    self.cache[row["query"]] = row

    def _cache_put(self, query: str, exec_time: float, result: Dict, success: bool, memory_delta: float) -> None:
        row = {
            "query": query,
            "exec_time": exec_time,
            "result": result,
            "success": success,
            "memory_delta": memory_delta,
        }
        self.cache[query] = row
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cache_file, "a") as f:
            f.write(json.dumps(row) + "\n")

    async def invoke_mcp_tool(self, query: str) -> Tuple[float, Dict, bool, float]:
        """Run the real 3-agent LangGraph workflow via AgentKit's REST facade
        (POST /api/workflow/run) and return (time, result, success, memory_delta).
        Spends LLM credits per call, so results are cached by query text —
        a re-run after an interruption skips every already-scored query."""
        cached = self.cache.get(query)
        if cached is not None:
            return cached["exec_time"], cached["result"], cached["success"], cached["memory_delta"]

        start_time = time.time()
        initial_memory = self.process.memory_info().rss / 1024 / 1024  # MB

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{AGENTKIT_URL}/api/workflow/run",
                    json={"question": query},
                    headers={"Content-Type": "application/json"},
                )

                execution_time = time.time() - start_time
                final_memory = self.process.memory_info().rss / 1024 / 1024  # MB
                memory_delta = final_memory - initial_memory

                if response.status_code == 200:
                    result = response.json()
                    success = "error" not in result
                else:
                    result = {
                        "error": f"HTTP {response.status_code}",
                        "detail": response.text,
                    }
                    success = False

                self._cache_put(query, execution_time, result, success, memory_delta)
                return execution_time, result, success, memory_delta

        except Exception as e:
            execution_time = time.time() - start_time
            final_memory = self.process.memory_info().rss / 1024 / 1024  # MB
            memory_delta = final_memory - initial_memory
            result = {"error": str(e)}
            self._cache_put(query, execution_time, result, False, memory_delta)
            return execution_time, result, False, memory_delta

    def evaluate_tool_selection(self, result: Dict, expected_tools: List[str]) -> bool:
        """Check whether the expected domain(s) were queried.

        analyst_agent() (workflow.py) keys its raw_data dict by domain, e.g.
        "finance_kpis"/"people_kpis"/"operations_kpis"/"customer_kpis"/
        "engineering_kpis"/"forecast_revenue" — that dict's keys ARE the tool
        selection signal here (not a literal MCP function name, since query_kpis
        etc. are shared across all 5 domains via a `domain=` parameter).
        """
        if "error" in result:
            return False

        raw_data = result.get("raw_data", {}) or {}
        return any(tool in raw_data for tool in expected_tools)

    def evaluate_report_quality(self, result: Dict, expected_fields: List[str]) -> bool:
        """Check if the report contains expected information"""
        if "error" in result:
            return False

        report = result.get("report", "").lower()
        return any(field in report for field in expected_fields)

    async def run_benchmark(self) -> Dict:
        """Run comprehensive MCP tools benchmark"""
        print("=== AgentKit MCP Tools Performance Benchmark ===")
        n_categories = len({s["category"] for s in TEST_SCENARIOS})
        print(f"Testing {len(TEST_SCENARIOS)} scenarios across {n_categories} tool categories")

        # Initialize category results
        for scenario in TEST_SCENARIOS:
            category = scenario["category"]
            if category not in self.results["category_results"]:
                self.results["category_results"][category] = {
                    "total": 0,
                    "successful": 0,
                    "correct_selection": 0,
                    "quality_pass": 0,
                    "total_time": 0,
                }

        for scenario in TEST_SCENARIOS:
            query = scenario["query"]
            category = scenario["category"]
            expected_tools = scenario["expected_tools"]
            expected_fields = scenario["expected_fields"]

            print(f"\n--- Testing: {query} ({category}) ---")

            exec_time, result, success, memory_delta = await self.invoke_mcp_tool(query)

            self.results["total_tests"] += 1
            self.results["execution_times"].append(exec_time)
            self.results["memory_samples"].append(memory_delta)

            category_results = self.results["category_results"][category]
            category_results["total"] += 1
            category_results["total_time"] += exec_time

            if success:
                self.results["successful"] += 1
                category_results["successful"] += 1

                # Evaluate tool selection
                selection_correct = self.evaluate_tool_selection(result, expected_tools)
                if selection_correct:
                    self.results["tool_selection_correct"] += 1
                    category_results["correct_selection"] += 1

                # Evaluate report quality
                quality_pass = self.evaluate_report_quality(result, expected_fields)
                if quality_pass:
                    self.results["report_quality"] += 1
                    category_results["quality_pass"] += 1

                print(
                    f"  Success: Yes | Time: {exec_time:.2f}s | Memory: {memory_delta:.1f}MB"
                )
                print(
                    f"  Tool Selection: {'✓' if selection_correct else '✗'} | Report Quality: {'✓' if quality_pass else '✗'}"
                )
            else:
                self.results["failed"] += 1
                print(f"  Success: No | Error: {result.get('error', 'Unknown')}")

        # Calculate aggregate metrics
        total_time = sum(self.results["execution_times"])
        avg_time = (
            total_time / len(self.results["execution_times"])
            if self.results["execution_times"]
            else 0
        )
        sorted_times = sorted(self.results["execution_times"])
        p95_time = sorted_times[int(len(sorted_times) * 0.95)] if sorted_times else 0

        avg_memory = (
            sum(self.results["memory_samples"]) / len(self.results["memory_samples"])
            if self.results["memory_samples"]
            else 0
        )
        max_memory = (
            max(self.results["memory_samples"]) if self.results["memory_samples"] else 0
        )

        tool_selection_accuracy = (
            (self.results["tool_selection_correct"] / self.results["total_tests"] * 100)
            if self.results["total_tests"] > 0
            else 0
        )
        execution_success_rate = (
            (self.results["successful"] / self.results["total_tests"] * 100)
            if self.results["total_tests"] > 0
            else 0
        )
        report_quality_rate = (
            (self.results["report_quality"] / self.results["total_tests"] * 100)
            if self.results["total_tests"] > 0
            else 0
        )

        print("\n=== Aggregate Results ===")
        print(f"Total tests: {self.results['total_tests']}")
        print(
            f"Successful: {self.results['successful']} ({execution_success_rate:.1f}%)"
        )
        print(f"Tool selection accuracy: {tool_selection_accuracy:.1f}%")
        print(f"Report quality: {report_quality_rate:.1f}%")
        print(f"Avg execution time: {avg_time:.2f}s")
        print(f"P95 execution time: {p95_time:.2f}s")
        print(f"Avg memory delta: {avg_memory:.1f}MB")
        print(f"Peak memory delta: {max_memory:.1f}MB")

        # Calculate category-specific metrics
        category_summary = {}
        for category, data in self.results["category_results"].items():
            if data["total"] > 0:
                category_summary[category] = {
                    "success_rate": (data["successful"] / data["total"] * 100),
                    "selection_accuracy": (
                        data["correct_selection"] / data["total"] * 100
                    ),
                    "quality_rate": (data["quality_pass"] / data["total"] * 100),
                    "avg_time": (data["total_time"] / data["total"]),
                }

        return {
            "tool_selection_accuracy": tool_selection_accuracy,
            "execution_success_rate": execution_success_rate,
            "avg_execution_time": avg_time,
            "p95_execution_time": p95_time,
            "report_quality_rate": report_quality_rate,
            "avg_memory": avg_memory,
            "max_memory": max_memory,
            "category_summary": category_summary,
        }


def update_benchmark_markdown(results: Dict):
    """Update the benchmark markdown with new results"""
    md_path = Path(__file__).resolve().parent / "MCP_TOOLS_BENCHMARK.md"

    from datetime import date

    content = f"""# AgentKit — MCP Tools Performance Benchmark

A comprehensive benchmark of AgentKit's MCP (Model Context Protocol) tools performance, accuracy, and resource utilization, run against the real 3-agent LangGraph workflow (`POST /api/workflow/run`). Reproducible:
`python eval/run_mcp_tools_benchmark.py`

## Setup
- Test Suite: {len(TEST_SCENARIOS)} standardized queries spanning all 5 seeded domains
- Tool Categories: Finance KPIs, People KPIs, Operations KPIs, Customer KPIs, Engineering KPIs, Forecasting, Anomalies
- Metrics: Domain-selection accuracy, execution time, memory usage, success rate
- Engine: Real 3-agent LangGraph workflow (Planner → Analyst → Reporter) via AgentKit's REST facade
- Database: PostgreSQL

## Results (real run, {date.today().isoformat()}, N={len(TEST_SCENARIOS)})

| Metric | Result |
|--------|--------|
| **Tool/Domain Selection Accuracy** | **{results['tool_selection_accuracy']:.1f}%** |
| **Tool Execution Success Rate** | **{results['execution_success_rate']:.1f}%** |
| **Avg Tool Execution Time** | **{results['avg_execution_time']:.1f}s** |
| **P95 Tool Execution Time** | **{results['p95_execution_time']:.1f}s** |
| **Report Generation Quality** | **{results['report_quality_rate']:.1f}%** |
| **Memory Peak per Tool** | **{results['max_memory']:.0f}MB** |

**Tool Breakdown:**

| Tool Category | Success Rate | Avg Time | Accuracy |
|---------------|--------------|----------|----------|
"""

    for category, metrics in results["category_summary"].items():
        content += f"| {category} | {metrics['success_rate']:.0f}% | {metrics['avg_time']:.1f}s | {metrics['selection_accuracy']:.0f}% |\n"

    with open(md_path, "w") as f:
        f.write(content)

    print(f"\nBenchmark results written to {md_path}")


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache-file", default=str(DEFAULT_CACHE_FILE),
                         help="JSONL cache of scored queries — reruns skip anything already cached")
    parser.add_argument("--reset", action="store_true", help="ignore/clear the existing cache and start fresh")
    parser.add_argument("--domains", default="all", help="kept for CLI compatibility; scenarios always cover all 5 domains")
    args = parser.parse_args()

    cache_path = Path(args.cache_file)
    if args.reset and cache_path.exists():
        cache_path.unlink()

    # Check if AgentKit server is running
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{AGENTKIT_URL}/health", timeout=5.0)
            if response.status_code != 200:
                print("Warning: AgentKit health check failed, continuing anyway...")
    except Exception as e:
        print(f"Warning: Could not connect to AgentKit at {AGENTKIT_URL}: {e}")
        print("Make sure AgentKit is running before benchmarking")
        return

    benchmark = MCPToolsBenchmark(cache_file=cache_path)
    results = await benchmark.run_benchmark()
    update_benchmark_markdown(results)


if __name__ == "__main__":
    asyncio.run(main())
