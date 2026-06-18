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

def _records(df, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """DataFrame → JSON-safe list of dicts (numpy scalars → native, NaN/Inf → None)."""
    import math
    recs = df.to_dict("records")
    if limit is not None:
        recs = recs[:limit]
    out: List[Dict[str, Any]] = []
    for r in recs:
        clean: Dict[str, Any] = {}
        for k, v in r.items():
            if hasattr(v, "item"):       # numpy scalar
                v = v.item()
            if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                v = None
            clean[k] = v
        out.append(clean)
    return out


async def query_kpis(
    domain: Optional[str] = None,
    period_from: Optional[str] = None,
    period_to: Optional[str] = None,
    metric_filter: Optional[str] = None,
    limit: int = 100,
) -> Dict[str, Any]:
    """Return KPI metrics for a domain and period window."""
    if not _PG:
        raise RuntimeError("AgentKit data layer unavailable: set POSTGRES_URL and seed kpi_metrics")
    try:
        df = get_kpi_metrics(categories=[domain] if domain else None)
        if df is None or df.empty:
            return {"kpis": [], "total": 0}
        if period_from:
            df = df[df["period"] >= period_from]
        if period_to:
            df = df[df["period"] <= period_to]
        if metric_filter:
            df = df[df["metric"].str.contains(metric_filter, case=False, na=False)]
        rows = _records(df, limit=limit)
        return {"kpis": rows, "total": len(rows)}
    except Exception as e:
        log.exception("query_kpis failed: %s", e)
        return {"kpis": [], "total": 0, "error": str(e)}


async def get_company_health(domain: Optional[str] = None) -> Dict[str, Any]:
    """Return composite company health index for a domain (or all)."""
    if not (_PG and _INSIGHTS):
        raise RuntimeError("AgentKit data layer unavailable: set POSTGRES_URL and seed kpi_metrics")
    try:
        df = get_kpi_metrics(categories=[domain] if domain else None)
        if df is None or df.empty:
            return {"score": 0.0, "interpretation": "no_data", "components": {}}
        h = compute_health_index(df)
        return {
            "score": float(h.get("score", 0.0)),
            "interpretation": h.get("label", "n/a"),
            "components": {k: h[k] for k in ("growth", "margin", "cash_score", "efficiency") if k in h},
        }
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
        raise RuntimeError("AgentKit data layer unavailable: set POSTGRES_URL and seed kpi_metrics")
    try:
        df = get_kpi_metrics(categories=[domain] if domain else None)
        if df is None or df.empty:
            return {"anomalies": [], "total": 0, "threshold": threshold, "method": method}
        out = detect_anomalies(df, z_threshold=threshold, method=method)
        if "is_anomaly" in out.columns:
            out = out[out["is_anomaly"] == True]  # noqa: E712
        cols = [c for c in ("metric", "category", "period", "value", "z_score") if c in out.columns]
        rows = _records(out[cols]) if not out.empty else []
        return {"anomalies": rows, "total": len(rows), "threshold": threshold, "method": method}
    except Exception as e:
        log.exception("detect_kpi_anomalies failed: %s", e)
        return {"anomalies": [], "total": 0, "threshold": threshold, "error": str(e)}


async def forecast_metric(
    metric_name: str,
    periods: int = 6,
    confidence_level: float = 0.95,
) -> Dict[str, Any]:
    """Forecast `periods` periods ahead for a named metric (Monte Carlo CI bands)."""
    if not (_PG and _FORECAST):
        raise RuntimeError("AgentKit data layer unavailable: set POSTGRES_URL and seed kpi_metrics")
    try:
        df = get_kpi_metrics(metrics=[metric_name])
        if df is None or df.empty:
            # name-tolerant fallback: case-insensitive exact, then substring match
            alldf = get_kpi_metrics()
            if alldf is not None and not alldf.empty:
                exact = alldf[alldf["metric"].str.lower() == metric_name.lower()]
                df = exact if not exact.empty else alldf[alldf["metric"].str.contains(metric_name, case=False, na=False)]
        if df is None or df.empty:
            return {"forecast": [], "upper_ci": [], "lower_ci": [], "method": "none", "note": "no_data"}
        fdf = (df[["period", "value"]].rename(columns={"period": "month_tag", "value": "actual"})
               .groupby("month_tag", as_index=False).agg({"actual": "mean"}).sort_values("month_tag"))
        res = ForecastEngine().time_series_forecast(fdf, periods=periods, confidence_level=confidence_level)
        if res is None or res.empty:
            return {"forecast": [], "upper_ci": [], "lower_ci": [], "method": "none", "note": "insufficient_history"}
        recs = res.to_dict("records")
        return {
            "metric": metric_name,
            "forecast": [{"period": r["month_tag"], "value": round(float(r["forecast"]), 2)} for r in recs],
            "lower_ci": [round(float(r["lower_bound"]), 2) for r in recs],
            "upper_ci": [round(float(r["upper_bound"]), 2) for r in recs],
            "confidence_level": confidence_level,
            "method": "linear_regression",
        }
    except Exception as e:
        log.exception("forecast_metric failed: %s", e)
        return {"forecast": [], "upper_ci": [], "lower_ci": [], "method": "error", "error": str(e)}


async def list_available_metrics(domain: Optional[str] = None) -> Dict[str, Any]:
    """Discovery tool: list metrics, categories, and periods (metrics scoped to domain if given)."""
    if not _PG:
        raise RuntimeError("AgentKit data layer unavailable: set POSTGRES_URL and seed kpi_metrics")
    try:
        metrics = get_available_metrics() or []
        if domain:
            df = get_kpi_metrics(categories=[domain])
            if df is not None and not df.empty:
                metrics = sorted(df["metric"].unique().tolist())
        return {
            "metrics": metrics,
            "categories": get_available_categories() or [],
            "periods": get_available_periods() or [],
        }
    except Exception as e:
        log.exception("list_available_metrics failed: %s", e)
        return {"metrics": [], "categories": [], "periods": [], "error": str(e)}


async def get_executive_summary() -> Dict[str, Any]:
    """Synthesize health, KPIs, and anomalies into a one-shot executive summary."""
    health = await get_company_health()
    kpis = await query_kpis(limit=10)
    anomalies = await detect_kpi_anomalies(domain="Finance") if _PG and _INSIGHTS else {"anomalies": []}
    return {
        "summary": "Executive snapshot generated by AgentKit",
        "health_score": health.get("score", 0.0),
        "interpretation": health.get("interpretation", "n/a"),
        "components": health.get("components", {}),
        "key_metrics": kpis.get("kpis", [])[:5],
        "anomalies": anomalies.get("anomalies", [])[:5],
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


def _serve_sse(port: int) -> None:
    """Serve SSE behind bearer-auth + rate-limit (gated by MCP_AUTH_TOKEN). Falls back to the
    plain FastMCP runner if the ASGI app can't be wrapped on this FastMCP version."""
    token = os.getenv("MCP_AUTH_TOKEN")
    if not token:
        log.warning("MCP_AUTH_TOKEN not set — SSE auth DISABLED (dev mode); rate-limit still on")
    try:
        import uvicorn
        from auth_middleware import BearerAuthRateLimit
        try:
            app = mcp.http_app(transport="sse")
        except TypeError:
            app = mcp.http_app()
        log.info("Serving SSE with auth=%s + rate-limit on :%s", bool(token), port)
        uvicorn.run(BearerAuthRateLimit(app), host="0.0.0.0", port=port)
    except Exception as e:
        log.warning("guarded SSE serve unavailable (%s) — falling back to mcp.run(sse)", e)
        mcp.run(transport="sse", host="0.0.0.0", port=port)


if __name__ == "__main__":
    if _FASTMCP:
        # When a cloud platform injects $PORT, default to HTTP/SSE so the service is reachable;
        # locally (no $PORT) default to stdio (the standard MCP transport for local clients).
        transport = os.getenv("MCP_TRANSPORT") or ("sse" if os.getenv("PORT") else "stdio")
        # Honor the platform-injected $PORT (Railway/Render/Fly) over MCP_PORT; default 8005.
        port = int(os.getenv("MCP_PORT") or os.getenv("PORT") or "8005")
        log.info("Starting AgentKit MCP server (transport=%s port=%s)...", transport, port)
        if transport == "sse":
            _serve_sse(port)
        else:
            mcp.run()
    else:
        log.error("fastmcp not installed; cannot start MCP server. pip install fastmcp")
