"""
AgentKit MCP Server — Business Intelligence tools for Claude/Cursor agents.

Exposes 6 tools, 6 resources, 1 prompt template.

Usage:
    python mcp_server.py
"""
from __future__ import annotations

import asyncio
import os
from typing import Any, Dict, List, Optional

from core.config import settings
from core.logger import get_logger

log = get_logger(__name__)

try:
    from fastmcp import FastMCP
    _FASTMCP = True
except ImportError:
    _FASTMCP = False
    log.warning("fastmcp not installed — MCP server not available")

# Optional imports — graceful degradation if DB not available
try:
    from services.pg_store import (
        get_kpi_metrics,
        get_available_metrics,
        get_available_categories,
        get_available_periods,
    )
    _PG = True
except Exception as e:
    log.warning("pg_store import failed (%s) — running in stub mode", e)
    _PG = False

try:
    from services.insights import compute_health_index, detect_anomalies
    _INSIGHTS = True
except Exception:
    _INSIGHTS = False

try:
    from services.forecasting import ForecastEngine
    _FORECAST = True
except Exception:
    _FORECAST = False


if _FASTMCP:
    mcp = FastMCP("AgentKit Business Intelligence")
else:
    mcp = None  # type: ignore


# ─────────────────────────────────────────────────────────────────────────────
# TOOLS
# ─────────────────────────────────────────────────────────────────────────────

async def query_kpis(
    domain: Optional[str] = None,
    period_from: Optional[str] = None,
    period_to: Optional[str] = None,
    metric_filter: Optional[str] = None,
    limit: int = 100,
) -> Dict[str, Any]:
    """Return KPI metrics for a domain and period window."""
    if not _PG:
        return {"kpis": [], "total": 0, "stub": True}
    try:
        kpis = get_kpi_metrics(category=domain) or []
        if period_from:
            kpis = [k for k in kpis if k.get("period", "") >= period_from]
        if period_to:
            kpis = [k for k in kpis if k.get("period", "") <= period_to]
        if metric_filter:
            kpis = [k for k in kpis if metric_filter.lower() in k.get("metric", "").lower()]
        kpis = kpis[:limit]
        return {"kpis": kpis, "total": len(kpis)}
    except Exception as e:
        log.exception("query_kpis failed: %s", e)
        return {"kpis": [], "total": 0, "error": str(e)}


async def get_company_health(domain: Optional[str] = None) -> Dict[str, Any]:
    """Return composite company health index for a domain (or all)."""
    if not (_PG and _INSIGHTS):
        return {"score": 0.0, "interpretation": "stub", "components": {}, "stub": True}
    try:
        kpis = get_kpi_metrics(category=domain) or []
        result = compute_health_index(kpis) if kpis else {"score": 0.0, "components": {}}
        return result if isinstance(result, dict) else {"score": float(result), "components": {}}
    except Exception as e:
        log.exception("get_company_health failed: %s", e)
        return {"score": 0.0, "interpretation": "error", "components": {}, "error": str(e)}


async def detect_kpi_anomalies(
    domain: str,
    method: str = "zscore",
    threshold: float = 2.5,
) -> Dict[str, Any]:
    """Find anomalies in a domain's KPI history."""
    if not (_PG and _INSIGHTS):
        return {"anomalies": [], "total": 0, "threshold": threshold, "stub": True}
    try:
        kpis = get_kpi_metrics(category=domain) or []
        anomalies = detect_anomalies(kpis, method=method, threshold=threshold) if kpis else []
        if not isinstance(anomalies, list):
            anomalies = []
        return {"anomalies": anomalies, "total": len(anomalies), "threshold": threshold, "method": method}
    except Exception as e:
        log.exception("detect_kpi_anomalies failed: %s", e)
        return {"anomalies": [], "total": 0, "threshold": threshold, "error": str(e)}


async def forecast_metric(
    metric_name: str,
    periods: int = 6,
    confidence_level: float = 0.95,
) -> Dict[str, Any]:
    """Forecast `periods` periods ahead for a named metric."""
    if not (_PG and _FORECAST):
        return {"forecast": [], "upper_ci": [], "lower_ci": [], "method": "stub", "stub": True}
    try:
        kpis = get_kpi_metrics(metric_filter=metric_name) or []
        if not kpis:
            return {"forecast": [], "upper_ci": [], "lower_ci": [], "method": "none", "note": "no_data"}
        engine = ForecastEngine()
        result = engine.time_series_forecast(kpis, periods=periods, confidence_level=confidence_level)
        return result if isinstance(result, dict) else {"forecast": result}
    except Exception as e:
        log.exception("forecast_metric failed: %s", e)
        return {"forecast": [], "upper_ci": [], "lower_ci": [], "method": "error", "error": str(e)}


async def list_available_metrics(domain: Optional[str] = None) -> Dict[str, Any]:
    """Discovery tool: list metrics, categories, and periods."""
    if not _PG:
        return {"metrics": [], "categories": [], "periods": [], "stub": True}
    try:
        return {
            "metrics": get_available_metrics(category=domain) or [],
            "categories": get_available_categories() or [],
            "periods": get_available_periods() or [],
        }
    except Exception as e:
        log.exception("list_available_metrics failed: %s", e)
        return {"metrics": [], "categories": [], "periods": [], "error": str(e)}


async def get_executive_summary() -> Dict[str, Any]:
    """Synthesize health, KPIs, anomalies, growth into a one-shot summary."""
    health = await get_company_health()
    kpis = await query_kpis(limit=10)
    return {
        "summary": "Executive snapshot generated by AgentKit",
        "health_score": health.get("score", 0.0),
        "interpretation": health.get("interpretation", "n/a"),
        "key_metrics": kpis.get("kpis", [])[:5],
        "anomalies": [],
        "top_growth": [],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Register with FastMCP (if available)
# ─────────────────────────────────────────────────────────────────────────────

if _FASTMCP:
    mcp.tool()(query_kpis)
    mcp.tool()(get_company_health)
    mcp.tool()(detect_kpi_anomalies)
    mcp.tool()(forecast_metric)
    mcp.tool()(list_available_metrics)
    mcp.tool()(get_executive_summary)

    @mcp.resource("kpi://Finance/latest")
    async def finance_latest() -> Dict[str, Any]:
        return await query_kpis(domain="Finance", limit=10)

    @mcp.resource("kpi://Growth/latest")
    async def growth_latest() -> Dict[str, Any]:
        return await query_kpis(domain="Growth", limit=10)

    @mcp.resource("kpi://Operations/latest")
    async def ops_latest() -> Dict[str, Any]:
        return await query_kpis(domain="Operations", limit=10)

    @mcp.resource("kpi://People/latest")
    async def people_latest() -> Dict[str, Any]:
        return await query_kpis(domain="People", limit=10)

    @mcp.resource("kpi://ESG/latest")
    async def esg_latest() -> Dict[str, Any]:
        return await query_kpis(domain="ESG", limit=10)

    @mcp.resource("kpi://IT_Ops/latest")
    async def itops_latest() -> Dict[str, Any]:
        return await query_kpis(domain="IT_Ops", limit=10)

    @mcp.prompt("monthly_executive_briefing")
    def monthly_briefing(month: str = "this month") -> str:
        return (
            f"Produce a monthly executive briefing for {month}. "
            "Sections: KEY FINDING, EVIDENCE (from KPI tools), ROOT CAUSE, "
            "RECOMMENDED ACTION, RISK IF UNADDRESSED. Be concrete and concise."
        )


if __name__ == "__main__":
    if _FASTMCP:
        transport = os.getenv("MCP_TRANSPORT", "stdio")
        port = int(os.getenv("MCP_PORT", "8005"))
        log.info("Starting AgentKit MCP server (transport=%s port=%s)...", transport, port)
        if transport == "sse":
            mcp.run(transport="sse", host="0.0.0.0", port=port)
        else:
            mcp.run()
    else:
        log.error("fastmcp not installed; cannot start MCP server. pip install fastmcp")
