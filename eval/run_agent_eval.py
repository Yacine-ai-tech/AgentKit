from agentkit_mcp.workflow import analyze


def main():
    print("Starting AgentKit LangGraph Workflow Evaluation...")

    # Simple list of queries to test the orchestrator
    test_queries = [
        {
            "query": "What drove company finance revenue recently?",
            "expected_tools": ["finance_kpis"],
        },
        {"query": "How is our headcount in People?", "expected_tools": ["people_kpis"]},
        {
            "query": "What is the forecast for revenue?",
            "expected_tools": ["forecast_revenue"],
        },
        {
            "query": "Are there any anomalies in our finance data?",
            "expected_tools": ["finance_anomalies"],
        },
    ]

    results = []

    for item in test_queries:
        query = item["query"]
        expected_tools = item["expected_tools"]
        print(f"\nEvaluating query: '{query}'")
        try:
            res = analyze(query)

            # Extract raw data to see what tools were invoked
            raw_data = res.get("raw_data", {})
            invoked = list(raw_data.keys())

            # Check if expected tools were executed
            passed_tools = all(tool in invoked for tool in expected_tools)
            has_report = len(res.get("report", "")) > 10

            passed = passed_tools and has_report
            print(f"  Invoked tools: {invoked}")
            print(f"  Has Report: {has_report}")
            print(f"  Passed: {passed}")
            results.append({"query": query, "passed": passed})
        except Exception as e:
            print(f"  Error evaluating {query}: {e}")
            results.append({"query": query, "passed": False})

    passed_count = sum(1 for r in results if r["passed"])
    total = len(results)

    print("\n--- RESULTS ---")
    print(
        f"Evaluation Complete! Score: {passed_count}/{total} ({(passed_count/total)*100 if total else 0:.1f}%)"
    )


if __name__ == "__main__":
    main()
