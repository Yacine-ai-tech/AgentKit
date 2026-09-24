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
import re
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


from agentkit_mcp.mcp_server import (
    detect_kpi_anomalies,  # noqa: E402
    forecast_metric,
    get_company_health,
    get_executive_summary,
    list_available_metrics,
    query_kpis,
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
                {
                    "role": "system",
                    "content": (
                        "You are a planner. Produce a concise 3-4 step plan for answering "
                        f"the question using available tools. Available metrics/categories: "
                        f"{json.dumps(metrics)[:1000]}"
                    ),
                },
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


_METRIC_NAME_RE = re.compile(r"\b[A-Z][a-zA-Z]*(?:_[A-Z][a-zA-Z]*)+\b")


def _forecast_target(raw_question: str) -> str:
    """Pick which metric to forecast from the question itself, instead of always
    forecasting revenue regardless of what was actually asked (e.g. a question about
    forecasting Customer_Churn_Rate or Operating_Expenses silently got a revenue
    forecast instead — found while extending eval/multi_domain_scenarios.json).
    KPI names in this project's questions are always written TitleCase_With_Underscores
    (see src/data/seed.py's BUSINESS_KPIS), so that's what we look for; forecast_metric()
    already does case-insensitive exact/substring matching against the real metric table,
    so passing the literal name through is enough. Falls back to "revenue" only when the
    question doesn't name a specific metric at all."""
    m = _METRIC_NAME_RE.search(raw_question)
    return m.group(0) if m else "revenue"


def _metric_derived_keywords() -> Dict[str, tuple]:
    """Keyword fragments derived from the real seeded KPI names themselves
    (src/data/seed.py's BUSINESS_KPIS), so the router's vocabulary can't silently drift
    out of sync with what metrics actually exist — found via eval/multi_domain_scenarios.json
    coverage: hand-picked keyword lists missed real KPIs like Employee_Satisfaction_Score
    (People), Supplier_On_Time_Delivery (Operations), and Code_Review_Turnaround
    (Engineering) entirely. Falls back to an empty dict (curated keywords still apply)
    if the seed module isn't importable in this context."""
    try:
        from src.data.seed import BUSINESS_KPIS
    except Exception:
        return {}
    derived: Dict[str, tuple] = {}
    for domain, metrics in BUSINESS_KPIS.items():
        if domain not in (
            "Finance", "People", "Operations", "Customer", "Engineering",
            "Growth", "Logistics", "ESG", "IT", "Security",
        ):
            continue
        words = set()
        for metric_name, *_ in metrics:
            for word in metric_name.lower().split("_"):
                if len(word) > 3:  # skip short/generic fragments ("of", "on", "the")
                    words.add(word)
        derived[domain] = tuple(words)
    return derived


_METRIC_KEYWORDS = _metric_derived_keywords()


async def analyst_agent(state: BusinessAnalysisState) -> BusinessAnalysisState:
    """Invoke MCP tools based on keywords in the question."""
    raw_q = (state.get("question") or "").lower()
    # Natural-language questions often embed a literal KPI/metric name in snake_case
    # (e.g. "How is our Supply_Chain_Fulfillment_Rate performing?"), which never matches
    # a keyword list written with spaces ("supply chain") — a real routing miss, found
    # via eval/run_dspy_eval.py's multi-domain suite (ops_001 silently querying nothing).
    # Normalizing underscores to spaces before matching keeps both phrasings working.
    q = raw_q.replace("_", " ")
    raw: Dict[str, Any] = {}
    # Anomaly detection was previously wired to the Finance branch only — an
    # "anomalies in Warehouse_Utilization" (Operations) or "anomalies in
    # Change_Failure_Rate" (Engineering) question silently got no anomaly check at
    # all, even though detect_kpi_anomalies() itself is already domain-generic. This
    # keyword is checked once, then applied to every domain actually matched below,
    # instead of being hardcoded to one domain.
    wants_anomalies = any(k in q for k in ("anomal", "unusual", "outlier"))
    # Domain routing by keywords — must match the real domain categories seeded in
    # src/data/seed.py's BUSINESS_KPIS (10 domains: the original 5 plus Growth/
    # Logistics/ESG/IT, mirroring IntelAI's taxonomy for cross-portfolio consistency,
    # plus Security). "mrr"/"arr" and "logistics" used to sit under Customer/Operations
    # respectively because Growth and Logistics didn't exist as domains yet — moved to
    # their own domains now that they do, rather than left as a stale workaround.
    domain_keywords = {
        "Finance": ("financ", "revenue", "margin", "cost", "profit"),
        "People": ("people", "hr", "headcount", "hiring", "turnover", "retention"),
        "Operations": ("operations", "supply chain", "warehouse", "defect"),
        "Customer": ("customer", "churn", "nps", "ltv", "support"),
        "Engineering": ("engineering", "deploy", "mttr", "sprint", "velocity", "incident"),
        "Growth": ("growth", "mrr", "arr", "recurring revenue", "expansion", "net revenue retention"),
        "Logistics": ("logistics", "freight", "shipment", "carrier", "last mile"),
        "ESG": ("esg", "emissions", "carbon", "renewable", "diversity", "sustainab"),
        "IT": ("uptime", "sla", "infrastructure cost", "patch", "network latency", "it ops"),
        "Security": ("security", "vulnerabilit", "phishing", "incident", "breach", "remediat"),
    }
    # Curated keywords cover general-language phrasing; metric-derived keywords cover a
    # question that names an exact KPI whose vocabulary the curated list never
    # anticipated (both checked — neither replaces the other).
    try:
        for domain, keywords in domain_keywords.items():
            all_keywords = keywords + _METRIC_KEYWORDS.get(domain, ())
            if not any(k in q for k in all_keywords):
                continue
            key = f"{domain.lower()}_kpis"
            raw[key] = await query_kpis(domain=domain)
            if wants_anomalies:
                raw[f"{domain.lower()}_anomalies"] = await detect_kpi_anomalies(domain=domain)
        if any(k in q for k in ("forecast", "projection", "predict")):
            target = _forecast_target(state.get("question") or "")
            raw[f"forecast_{target.lower()}"] = await forecast_metric(target, periods=6)
        if any(k in q for k in ("available metric", "what metric", "list metric", "which metric")):
            raw["available_metrics"] = await list_available_metrics()

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
                {
                    "role": "system",
                    "content": (
                        "You synthesize raw data into an executive report with these sections: "
                        "KEY FINDING, EVIDENCE, ROOT CAUSE, RECOMMENDED ACTION, RISK IF UNADDRESSED. "
                        "Be concrete. Cite numbers. Be brief."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Question: {state.get('question')}\n\n"
                        f"Plan: {state.get('plan', '')}\n\n"
                        f"Raw data: {json.dumps(state.get('raw_data', {}))[:6000]}"
                    ),
                },
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
            upper = (
                line.strip().strip("#*").strip().rstrip(":").strip("#*").strip().upper()
            )
            if upper in {
                "KEY FINDING",
                "EVIDENCE",
                "ROOT CAUSE",
                "RECOMMENDED ACTION",
                "RISK IF UNADDRESSED",
            }:
                if current:
                    sections[current.lower().replace(" ", "_")] = "\n".join(
                        buffer
                    ).strip()
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
