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
