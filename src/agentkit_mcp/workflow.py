"""
AgentKit LangGraph workflow — 3-agent business analysis chain.

planner_agent  (LLM_REASONING)  → produces a 3-4 step plan
analyst_agent  (LLM_DEFAULT)    → invokes MCP tools, gathers raw_data
reporter_agent (LLM_REASONING)  → synthesizes executive report

Public API:
    from agentkit_mcp.workflow import analyze
    result = analyze("What drove gross margin in Q1?")
"""
from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List, Optional, TypedDict

from agentkit_mcp.core.logger import get_logger

log = get_logger(__name__)

try:
    from langgraph.graph import END, StateGraph
    _LANGGRAPH = True
except ImportError:
    _LANGGRAPH = False
    log.warning("langgraph not installed — workflow will not run")

from agentkit_mcp.core.llm_router import LLMUnavailable, llm_call  # noqa: E402

try:
    import litellm  # noqa: F401  (routing goes through llm_router; this is a presence check)
    _LITELLM = True
except ImportError:
    _LITELLM = False


from agentkit_mcp.mcp_server import (  # noqa: E402
    query_kpis,
    get_company_health,
    detect_kpi_anomalies,
    forecast_metric,
    list_available_metrics,
    get_executive_summary,
)


class BusinessAnalysisState(TypedDict, total=False):
    question: str
    plan: str
    tool_calls: List[Dict[str, Any]]
    raw_data: Dict[str, Any]
    report: str
    report_sections: Dict[str, str]
    error: Optional[str]


async def planner_agent(state: BusinessAnalysisState) -> BusinessAnalysisState:
    """Break the question into a 3-4 step plan."""
    if not _LITELLM:
        state["plan"] = "stub_plan: tool_a → tool_b → synthesize"
        return state
    try:
        metrics = await list_available_metrics()
        resp = await llm_call(
            [
                {"role": "system", "content": (
                    "You are a planner. Produce a concise 3-4 step plan for answering "
                    f"the question using available tools. Available metrics/categories: "
                    f"{json.dumps(metrics)[:1000]}"
                )},
                {"role": "user", "content": state["question"]},
            ],
            tier="reasoning",
            temperature=0.3,
        )
        state["plan"] = resp.choices[0].message.content or ""
    except LLMUnavailable as e:
        log.warning("planner_agent: no model available (%s)", e)
        state["error"] = str(e)
    except Exception as e:
        log.exception("planner_agent failed: %s", e)
        state["error"] = str(e)
    return state


async def analyst_agent(state: BusinessAnalysisState) -> BusinessAnalysisState:
    """Invoke MCP tools based on keywords in the question."""
    q = (state.get("question") or "").lower()
    raw: Dict[str, Any] = {}
    try:
        # Domain routing by keywords
        if any(k in q for k in ("finance", "revenue", "margin", "cost", "profit")):
            raw["finance_kpis"] = await query_kpis(domain="Finance")
            raw["finance_anomalies"] = await detect_kpi_anomalies(domain="Finance")
        if any(k in q for k in ("people", "hr", "headcount", "hiring")):
            raw["people_kpis"] = await query_kpis(domain="People")
        if any(k in q for k in ("growth", "customer", "mrr", "arr")):
            raw["growth_kpis"] = await query_kpis(domain="Growth")
        if any(k in q for k in ("forecast", "projection", "predict")):
            raw["forecast_revenue"] = await forecast_metric("revenue", periods=6)

        # Always include
        raw["company_health"] = await get_company_health()
        raw["executive_summary"] = await get_executive_summary()
        state["raw_data"] = raw
    except Exception as e:
        log.exception("analyst_agent failed: %s", e)
        state["error"] = str(e)
        state["raw_data"] = raw
    return state


async def reporter_agent(state: BusinessAnalysisState) -> BusinessAnalysisState:
    """Synthesize raw_data into an executive report."""
    if not _LITELLM:
        state["report"] = "stub_report: data was gathered but no LLM is configured"
        state["report_sections"] = {"key_finding": "stub"}
        return state
    try:
        resp = await llm_call(
            [
                {"role": "system", "content": (
                    "You synthesize raw data into an executive report with these sections: "
                    "KEY FINDING, EVIDENCE, ROOT CAUSE, RECOMMENDED ACTION, RISK IF UNADDRESSED. "
                    "Be concrete. Cite numbers. Be brief."
                )},
                {"role": "user", "content": (
                    f"Question: {state.get('question')}\n\n"
                    f"Plan: {state.get('plan', '')}\n\n"
                    f"Raw data: {json.dumps(state.get('raw_data', {}))[:6000]}"
                )},
            ],
            tier="reasoning",
            temperature=0.2,
        )
        text = resp.choices[0].message.content or ""
        state["report"] = text
        # Naive section parser
        sections: Dict[str, str] = {}
        current = None
        buffer: List[str] = []
        for line in text.splitlines():
            # tolerate markdown headers: "## KEY FINDING", "**KEY FINDING**", "KEY FINDING:"
            upper = line.strip().strip("#*").strip().rstrip(":").strip("#*").strip().upper()
            if upper in {"KEY FINDING", "EVIDENCE", "ROOT CAUSE", "RECOMMENDED ACTION", "RISK IF UNADDRESSED"}:
                if current:
                    sections[current.lower().replace(" ", "_")] = "\n".join(buffer).strip()
                current = upper
                buffer = []
            else:
                buffer.append(line)
        if current:
            sections[current.lower().replace(" ", "_")] = "\n".join(buffer).strip()
        state["report_sections"] = sections
    except LLMUnavailable as e:
        log.warning("reporter_agent: no model available (%s)", e)
        state["error"] = str(e)
    except Exception as e:
        log.exception("reporter_agent failed: %s", e)
        state["error"] = str(e)
    return state


def _build_graph():
    if not _LANGGRAPH:
        return None
    g = StateGraph(BusinessAnalysisState)
    g.add_node("planner", planner_agent)
    g.add_node("analyst", analyst_agent)
    g.add_node("reporter", reporter_agent)
    g.set_entry_point("planner")
    g.add_edge("planner", "analyst")
    g.add_edge("analyst", "reporter")
    g.add_edge("reporter", END)
    return g.compile()


_GRAPH = _build_graph()


def analyze(question: str) -> Dict[str, Any]:
    """Run the full 3-agent analysis. Returns the final state as a dict."""
    if _GRAPH is None:
        return {
            "question": question,
            "report": "stub: langgraph not installed",
            "error": "langgraph_not_installed",
        }
    initial: BusinessAnalysisState = {"question": question}
    final = asyncio.run(_GRAPH.ainvoke(initial))
    return dict(final)


if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:]) or "What's our company's overall health right now?"
    out = analyze(q)
    print(json.dumps(out, indent=2, default=str))
