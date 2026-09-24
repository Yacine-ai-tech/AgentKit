import pytest


@pytest.mark.unit
def test_workflow_logic():
    # LangGraph 3-node workflow mock test
    workflow_state = {"messages": [], "analysis": ""}

    def fetch_data_node(state):
        state["data"] = {"kpi": 95}
        return state

    def analyze_node(state):
        state["analysis"] = f"KPI is {state['data']['kpi']}"
        return state

    def report_node(state):
        state["report"] = f"Final Report: {state['analysis']}"
        return state

    state = fetch_data_node(workflow_state)
    state = analyze_node(state)
    state = report_node(state)

    assert state["report"] == "Final Report: KPI is 95"


# ---------------------------------------------------------------------------
# analyst_agent() keyword routing — real bugs found via eval/run_dspy_eval.py's
# multi-domain suite, fixed in workflow.py.
# ---------------------------------------------------------------------------
import asyncio

from agentkit_mcp import workflow as wf


def _mock_tools(monkeypatch, calls):
    """Record every domain-tool call the routing makes, without hitting a real DB."""

    async def _query_kpis(domain):
        calls.append(("query_kpis", domain))
        return {"domain": domain}

    async def _detect_anomalies(domain):
        calls.append(("detect_kpi_anomalies", domain))
        return {"domain": domain, "anomalies": []}

    async def _forecast(metric, periods=6):
        calls.append(("forecast_metric", metric))
        return {"metric": metric}

    async def _list_metrics():
        calls.append(("list_available_metrics", None))
        return {"metrics": []}

    async def _company_health():
        return {"score": 90}

    async def _exec_summary():
        return {"summary": "ok"}

    monkeypatch.setattr(wf, "query_kpis", _query_kpis)
    monkeypatch.setattr(wf, "detect_kpi_anomalies", _detect_anomalies)
    monkeypatch.setattr(wf, "forecast_metric", _forecast)
    monkeypatch.setattr(wf, "list_available_metrics", _list_metrics)
    monkeypatch.setattr(wf, "get_company_health", _company_health)
    monkeypatch.setattr(wf, "get_executive_summary", _exec_summary)


def test_analyst_agent_matches_underscored_kpi_names(monkeypatch):
    """Real bug: a question quoting a literal snake_case KPI name (as production
    dashboards commonly do) never matched a keyword list written with spaces —
    'Supply_Chain_Fulfillment_Rate' contains no literal 'supply chain' substring."""
    calls = []
    _mock_tools(monkeypatch, calls)
    state = {"question": "How is our Supply_Chain_Fulfillment_Rate performing this quarter?"}
    asyncio.run(wf.analyst_agent(state))
    assert ("query_kpis", "Operations") in calls


def test_analyst_agent_anomaly_detection_not_hardcoded_to_finance(monkeypatch):
    """Real bug: detect_kpi_anomalies was only ever called on the Finance branch,
    regardless of which domain the question actually asked about — an Operations or
    Engineering anomaly question silently got no anomaly check run at all, even
    though the underlying tool is already domain-generic."""
    calls = []
    _mock_tools(monkeypatch, calls)
    state = {"question": "Are there anomalies in our Warehouse_Utilization?"}
    asyncio.run(wf.analyst_agent(state))
    assert ("detect_kpi_anomalies", "Operations") in calls

    calls.clear()
    state = {"question": "Are there any anomalies in our Change_Failure_Rate or Sprint_Velocity?"}
    asyncio.run(wf.analyst_agent(state))
    assert ("detect_kpi_anomalies", "Engineering") in calls


def test_analyst_agent_anomaly_detection_is_keyword_gated_not_unconditional(monkeypatch):
    """Finance anomaly detection used to run on every finance-domain question, even
    ones that never asked about anomalies at all. Now gated on the same anomaly
    keywords as every other domain, for consistency."""
    calls = []
    _mock_tools(monkeypatch, calls)
    state = {"question": "What drove our Monthly_Revenue growth over the last 6 months?"}
    asyncio.run(wf.analyst_agent(state))
    assert ("query_kpis", "Finance") in calls
    assert ("detect_kpi_anomalies", "Finance") not in calls


def test_analyst_agent_routes_to_list_available_metrics(monkeypatch):
    """list_available_metrics is a real, existing MCP tool that was simply never
    wired into the keyword router — not a missing feature, a missing connection."""
    calls = []
    _mock_tools(monkeypatch, calls)
    state = {"question": "What metrics are available across Finance and Engineering?"}
    asyncio.run(wf.analyst_agent(state))
    assert ("list_available_metrics", None) in calls


def test_analyst_agent_forecasts_the_metric_actually_asked_about(monkeypatch):
    """Real bug: forecast_metric() was always called with a hardcoded 'revenue' target
    regardless of which metric the question actually named."""
    calls = []
    _mock_tools(monkeypatch, calls)
    state = {"question": "Forecast our Operating_Expenses for the next 3 months."}
    asyncio.run(wf.analyst_agent(state))
    assert ("forecast_metric", "Operating_Expenses") in calls
    assert not any(c == ("forecast_metric", "revenue") for c in calls)


def test_analyst_agent_forecast_falls_back_to_revenue_without_a_named_metric(monkeypatch):
    calls = []
    _mock_tools(monkeypatch, calls)
    state = {"question": "Forecast our numbers for next quarter."}
    asyncio.run(wf.analyst_agent(state))
    assert ("forecast_metric", "revenue") in calls


def test_analyst_agent_routes_on_metric_derived_keywords(monkeypatch):
    """Real gaps found extending eval/multi_domain_scenarios.json: several real KPI
    names never matched the curated (hand-picked) keyword lists at all, e.g.
    Employee_Satisfaction_Score (People), Supplier_On_Time_Delivery (Operations),
    Code_Review_Turnaround (Engineering). Fixed by deriving extra keywords from the
    real seeded metric names (src/agentkit_mcp/data/seed.py) rather than patching the hand-picked
    list one miss at a time."""
    calls = []
    _mock_tools(monkeypatch, calls)
    state = {"question": "Are there any anomalies in our Employee_Satisfaction_Score?"}
    asyncio.run(wf.analyst_agent(state))
    assert ("query_kpis", "People") in calls

    calls.clear()
    state = {"question": "What is our Supplier_On_Time_Delivery rate?"}
    asyncio.run(wf.analyst_agent(state))
    assert ("query_kpis", "Operations") in calls

    calls.clear()
    state = {"question": "What is our current Code_Review_Turnaround time?"}
    asyncio.run(wf.analyst_agent(state))
    assert ("query_kpis", "Engineering") in calls


def test_analyst_agent_matches_financial_adjective_form(monkeypatch):
    """Real bug found via eval/run_mcp_tools_benchmark.py's live run: the keyword
    'finance' is not a substring of 'financial' (they diverge at the 7th letter), so
    'Are there any anomalies in the financial data?' matched no Finance keyword at all
    and silently queried nothing. Fixed by using the shorter stem 'financ', which
    matches finance/financial/financing alike."""
    calls = []
    _mock_tools(monkeypatch, calls)
    state = {"question": "Are there any anomalies in the financial data?"}
    asyncio.run(wf.analyst_agent(state))
    assert ("query_kpis", "Finance") in calls
    assert ("detect_kpi_anomalies", "Finance") in calls
