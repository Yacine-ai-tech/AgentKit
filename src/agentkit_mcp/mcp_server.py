"""
AgentKit MCP Server — a generic, policy-gated MCP server for Claude/Cursor agents.
Tools, resources, and prompts are supplied by whatever packs are configured; the
bundled reference pack exposes tools across Finance, People, Operations, Customer,
and Engineering domains (not just business intelligence), but AgentKit itself is
data-, resource-, prompt-, and tool-agnostic.

The reference pack currently exposes 9 tools (read, write, and destructive
effect-classed, gated by `policy.py`), 0 resources, 0 prompt templates.

Usage:
    python mcp_server.py
"""

from __future__ import annotations

import os
from functools import partial
from typing import Any, Dict, List, Optional

import anyio

from agentkit_mcp.core.logger import get_logger
from agentkit_mcp.core.policy import READ, ToolPolicy, policy_engine
from agentkit_mcp.pack_runtime import register_pack_tools
from agentkit_mcp.services.pg_store import (
    get_available_categories,
    get_available_metrics,
    get_available_periods,
    get_kpi_metrics,
)
from agentkit_mcp.toolpacks import load_packs

log = get_logger(__name__)


async def _run_db(fn, *args, **kwargs):
    """Run a blocking pg_store call (psycopg network I/O) in a worker thread.

    query_kpis/get_company_health/etc. are `async def` but pg_store's functions are
    plain sync psycopg calls — calling them directly here would block the single
    asyncio event loop the SSE/HTTP server shares across every concurrent connection,
    serializing unrelated requests behind whatever DB call happens to be in flight.
    """
    return await anyio.to_thread.run_sync(partial(fn, *args, **kwargs))


try:
    from fastmcp import FastMCP

    _FASTMCP = True
except ImportError:
    _FASTMCP = False
    log.warning("fastmcp not installed — MCP server not available")

_PG = True

try:
    from agentkit_mcp.services.insights import compute_health_index, detect_anomalies

    _INSIGHTS = True
except Exception:
    _INSIGHTS = False
    log.exception("insights module unavailable — health-score/anomalies disabled")

try:
    from agentkit_mcp.services.forecasting import ForecastEngine

    _FORECAST = True
except Exception:
    _FORECAST = False
    log.exception("forecasting module unavailable — forecast disabled")


if _FASTMCP:
    mcp = FastMCP("AgentKit Business Intelligence")
else:
    mcp = None  # type: ignore

# Declarative tool packs, populated below when FastMCP is available. Defined here so
# importers (web_app's /api/packs) always find the attribute, even in a minimal install.
PACKS: Dict[str, Any] = {}


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
            if hasattr(v, "item"):  # numpy scalar
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
    """Retrieve historical and real-time Key Performance Indicators (KPIs) from the governed Postgres store.

    Fetches structured time-series metrics across enterprise business domains including Finance,
    People (HR), Operations, Customer (Sales/Support), Engineering, Growth, Logistics, ESG, IT,
    and Security.

    Args:
        domain: Optional taxonomy category filter (e.g. 'Finance', 'People', 'Operations',
            'Customer', 'Engineering', 'Growth', 'ESG', 'IT', 'Security'). Omit to query across all domains.
        period_from: Optional start period in 'YYYY-MM' format (e.g. '2024-01'). Inclusive lower bound.
        period_to: Optional end period in 'YYYY-MM' format (e.g. '2026-06'). Inclusive upper bound.
        metric_filter: Optional substring or exact metric name match (e.g. 'revenue', 'churn_rate',
            'gross_margin', 'cac', 'headcount'). Case-insensitive.
        limit: Maximum number of metric records to return. Defaults to 100 (range: 1 to 500).

    Returns:
        A dictionary containing:
            - 'kpis': List of metric objects, each with 'id', 'metric', 'category', 'period',
              'value', 'unit', and 'source'.
            - 'total': Integer count of retrieved metric records.
    """
    if not _PG:
        raise RuntimeError(
            "AgentKit data layer unavailable: set POSTGRES_URL and seed kpi_metrics"
        )
    try:
        cats = None
        if domain and str(domain).strip().lower() not in ("all", "company", "global", "total", "*", "none", "null"):
            cats = [domain.strip()]
        df = await _run_db(
            get_kpi_metrics,
            categories=cats,
            period_from=period_from,
            period_to=period_to,
            metric_filter=metric_filter,
            limit=limit,
        )
        if df is None or df.empty:
            return {"kpis": [], "total": 0}
        rows = _records(df)
        return {"kpis": rows, "total": len(rows)}
    except Exception as e:
        log.exception("query_kpis failed: %s", e)
        return {"kpis": [], "total": 0, "error": str(e)}


async def get_company_health(domain: Optional[str] = None) -> Dict[str, Any]:
    """Compute composite organizational health scores and diagnostic health index breakdown.

    Synthesizes multi-factor business performance indicators into a holistic 0-100 health score
    with categorized qualitative interpretations ('Optimal', 'Healthy', 'Warning', 'Critical')
    and sub-component scores across growth rate, profit margins, cash runway, and operational efficiency.

    Args:
        domain: Optional business domain to compute isolated departmental health for (e.g. 'Finance',
            'Operations', 'Customer', 'Growth'). If omitted or None, calculates company-wide aggregate health.

    Returns:
        A dictionary containing:
            - 'score': Floating-point aggregate health index from 0.0 to 100.0.
            - 'interpretation': Qualitative status assessment string ('Optimal', 'Healthy', 'Warning', 'Critical').
            - 'components': Dictionary of granular sub-scores:
                - 'growth': Year-over-year expansion and revenue momentum score.
                - 'margin': Unit economics, EBITDA, and gross margin health score.
                - 'cash_score': Cash runway longevity and liquidity ratio index.
                - 'efficiency': Operational efficiency, headcount leverage, and burn multiple.
    """
    if not (_PG and _INSIGHTS):
        raise RuntimeError(
            "AgentKit data layer unavailable: set POSTGRES_URL and seed kpi_metrics"
        )
    try:
        cats = None
        if domain and str(domain).strip().lower() not in ("all", "company", "global", "total", "*", "none", "null"):
            cats = [domain.strip()]
        df = await _run_db(get_kpi_metrics, categories=cats)
        if df is None or df.empty:
            return {"score": 0.0, "interpretation": "no_data", "components": {}}
        h = compute_health_index(df)
        return {
            "score": float(h.get("score", 0.0)),
            "interpretation": h.get("label", "n/a"),
            "components": {
                k: h[k]
                for k in ("growth", "margin", "cash_score", "efficiency")
                if k in h
            },
        }
    except Exception as e:
        log.exception("get_company_health failed: %s", e)
        return {
            "score": 0.0,
            "interpretation": "error",
            "components": {},
            "error": str(e),
        }


async def detect_kpi_anomalies(
    domain: str,
    method: str = "zscore",
    threshold: float = 2.5,
) -> Dict[str, Any]:
    """Detect statistical anomalies, sudden spikes, and unexpected deviations in KPI time-series history.

    Analyzes metric historical distributions within a specified business domain using rigorous
    parametric (Z-Score) or non-parametric (IQR - Interquartile Range) anomaly detection algorithms
    to identify operational risks, unexpected budget variances, or sudden performance degradation.

    Args:
        domain: Target business domain to evaluate (e.g. 'Finance', 'Operations', 'Customer',
            'People', 'Engineering', 'Growth', 'ESG', 'IT'). Required.
        method: Statistical anomaly detection algorithm to execute. Options:
            - 'zscore': Standard deviation testing for normally distributed metrics (default).
            - 'iqr': Robust quartile range testing for skewed or fat-tailed metric distributions.
        threshold: Sensitivity cutoff factor for classification. For 'zscore', specifies standard
            deviations from mean (default: 2.5). For 'iqr', specifies multiplier above Q3/below Q1 (default: 1.5).

    Returns:
        A dictionary containing:
            - 'anomalies': List of anomalous metric records, each containing 'metric', 'category',
              'period', 'value', and calculated 'z_score' deviation magnitude.
            - 'total': Total number of detected statistical anomalies.
            - 'threshold': The numerical sensitivity threshold utilized.
            - 'method': The statistical algorithm applied.
    """
    if not (_PG and _INSIGHTS):
        raise RuntimeError(
            "AgentKit data layer unavailable: set POSTGRES_URL and seed kpi_metrics"
        )
    try:
        cats = None
        if domain and str(domain).strip().lower() not in ("all", "company", "global", "total", "*", "none", "null"):
            cats = [domain.strip()]
        df = await _run_db(get_kpi_metrics, categories=cats)
        if df is None or df.empty:
            return {
                "anomalies": [],
                "total": 0,
                "threshold": threshold,
                "method": method,
            }
        out = detect_anomalies(df, z_threshold=threshold, method=method)
        if "is_anomaly" in out.columns:
            out = out[out["is_anomaly"] == True]  # noqa: E712
        cols = [
            c
            for c in ("metric", "category", "period", "value", "z_score")
            if c in out.columns
        ]
        rows = _records(out[cols]) if not out.empty else []
        return {
            "anomalies": rows,
            "total": len(rows),
            "threshold": threshold,
            "method": method,
        }
    except Exception as e:
        log.exception("detect_kpi_anomalies failed: %s", e)
        return {"anomalies": [], "total": 0, "threshold": threshold, "error": str(e)}


async def forecast_metric(
    metric_name: str,
    periods: int = 6,
    confidence_level: float = 0.95,
) -> Dict[str, Any]:
    """Generate forward-looking time-series forecasts with Monte Carlo confidence intervals for a named KPI.

    Applies trend analysis and linear projection mathematical modeling over historical monthly metric data
    to predict future trajectory across specified forward horizon periods, providing upper and lower
    bound confidence intervals.

    Args:
        metric_name: Exact or substring name of the KPI metric to forecast (e.g. 'revenue', 'mrr',
            'gross_margin', 'headcount', 'cac', 'active_users', 'churn_rate').
        periods: Number of monthly periods ahead to project. Defaults to 6 periods (range: 1 to 24).
        confidence_level: Statistical confidence interval band width (e.g. 0.95 for 95% confidence interval).
            Defaults to 0.95.

    Returns:
        A dictionary containing:
            - 'metric': Canonical name of the evaluated KPI metric.
            - 'forecast': List of forecast objects with forward 'period' ('YYYY-MM') and projected 'value'.
            - 'lower_ci': List of lower-bound confidence threshold values matching forecast horizon.
            - 'upper_ci': List of upper-bound confidence threshold values matching forecast horizon.
            - 'confidence_level': The statistical confidence level applied.
            - 'method': The forecasting algorithm utilized (e.g. 'linear_regression').
    """
    if not (_PG and _FORECAST):
        if not _PG:
            raise RuntimeError("AgentKit data layer unavailable: set POSTGRES_URL and seed kpi_metrics")
        raise RuntimeError(
            "Forecasting module failed to import (see startup logs for the real cause — "
            "commonly a missing 'scipy' install, since services/forecasting.py imports it)"
        )
    try:
        df = await _run_db(get_kpi_metrics, metrics=[metric_name])
        if df is None or df.empty:
            alldf = await _run_db(get_kpi_metrics)
            if alldf is not None and not alldf.empty:
                exact = alldf[alldf["metric"].str.lower() == metric_name.lower()]
                df = (
                    exact
                    if not exact.empty
                    else alldf[
                        alldf["metric"].str.contains(metric_name, case=False, na=False)
                    ]
                )
        if df is None or df.empty:
            return {
                "forecast": [],
                "upper_ci": [],
                "lower_ci": [],
                "method": "none",
                "note": "no_data",
            }
        fdf = (
            df[["period", "value"]]
            .rename(columns={"period": "month_tag", "value": "actual"})
            .groupby("month_tag", as_index=False)
            .agg({"actual": "mean"})
            .sort_values("month_tag")
        )
        res = ForecastEngine().time_series_forecast(
            fdf, periods=periods, confidence_level=confidence_level
        )
        if res is None or res.empty:
            return {
                "forecast": [],
                "upper_ci": [],
                "lower_ci": [],
                "method": "none",
                "note": "insufficient_history",
            }
        recs = res.to_dict("records")
        return {
            "metric": metric_name,
            "forecast": [
                {"period": r["month_tag"], "value": round(float(r["forecast"]), 2)}
                for r in recs
            ],
            "lower_ci": [round(float(r["lower_bound"]), 2) for r in recs],
            "upper_ci": [round(float(r["upper_bound"]), 2) for r in recs],
            "confidence_level": confidence_level,
            "method": "linear_regression",
        }
    except Exception as e:
        log.exception("forecast_metric failed: %s", e)
        return {
            "forecast": [],
            "upper_ci": [],
            "lower_ci": [],
            "method": "error",
            "error": str(e),
        }


async def list_available_metrics(domain: Optional[str] = None) -> Dict[str, Any]:
    """Discover all supported KPI metrics, business domains, and available historical time periods.

    Essential discovery tool for agents to inspect the metadata schema before formulating specific
    queries, anomaly detections, or predictive forecasts.

    Args:
        domain: Optional business category to filter metric names by (e.g. 'Finance', 'People',
            'Operations', 'Customer', 'Engineering'). If omitted, returns all global metrics.

    Returns:
        A dictionary containing:
            - 'metrics': Alphabetically sorted list of all unique KPI metric identifier strings.
            - 'categories': List of available business domain category names.
            - 'periods': Chronologically sorted list of all historical recording periods ('YYYY-MM').
    """
    if not _PG:
        raise RuntimeError(
            "AgentKit data layer unavailable: set POSTGRES_URL and seed kpi_metrics"
        )
    try:
        metrics = await _run_db(get_available_metrics) or []
        if domain:
            df = await _run_db(get_kpi_metrics, categories=[domain])
            if df is not None and not df.empty:
                metrics = sorted(df["metric"].unique().tolist())
        return {
            "metrics": metrics,
            "categories": await _run_db(get_available_categories) or [],
            "periods": await _run_db(get_available_periods) or [],
        }
    except Exception as e:
        log.exception("list_available_metrics failed: %s", e)
        return {"metrics": [], "categories": [], "periods": [], "error": str(e)}


async def get_executive_summary() -> Dict[str, Any]:
    """Generate a comprehensive one-shot executive briefing synthesizing health, key metrics, and anomalies.

    Executes a high-level cross-domain synthesis combining composite organizational health diagnostics,
    primary KPI indicators, and active statistical anomalies across Finance, Operations, and Growth into
    an actionable briefing for leadership.

    Returns:
        A dictionary containing:
            - 'summary': High-level descriptive briefing title.
            - 'health_score': Overall company health index (0.0 to 100.0).
            - 'interpretation': Overall company health classification string ('Optimal', 'Healthy', 'Warning', 'Critical').
            - 'components': Breakdown of health scores (growth, margin, cash_score, efficiency).
            - 'key_metrics': Top 5 representative business KPI metric records.
            - 'anomalies': Top 5 active statistical anomalies requiring immediate executive review.
    """
    health = await get_company_health()
    kpis = await query_kpis(limit=10)
    anomalies = (
        await detect_kpi_anomalies(domain="Finance")
        if _PG and _INSIGHTS
        else {"anomalies": []}
    )
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

    # The six built-ins are read-only, but they're registered with the same policy
    # engine as declarative tools so `/api/policy` describes the whole surface — a
    # reviewer shouldn't have to read source to learn which tools can cause effects.
    for _name, _desc in (
        ("query_kpis", "Return KPI metrics for a domain and period window."),
        ("get_company_health", "Composite company health index."),
        ("detect_kpi_anomalies", "Find anomalies in a domain's KPI history."),
        ("forecast_metric", "Forecast N periods ahead for a named metric."),
        ("list_available_metrics", "Discovery: metrics, categories, periods."),
        ("get_executive_summary", "One-shot synthesis of health, KPIs and anomalies."),
    ):
        policy_engine.register(ToolPolicy(name=_name, effect=READ, description=_desc))

    # Declarative tool packs (YAML). Additive: a deployment with no packs configured
    # behaves exactly as before, so this cannot break an existing install.
    try:
        PACKS = load_packs()
        if PACKS:
            register_pack_tools(mcp, PACKS)
    except Exception as e:  # never let a bad pack stop the server from serving
        log.error("tool pack loading failed: %s", e)
        PACKS = {}

    # MCP resources — one per real seeded domain (README previously advertised these
    # under domain names ("Growth", "ESG", "IT_Ops") that, at the time, didn't exist
    # anywhere in this project's own seed data — copied from a different project's
    # domain list and never actually implemented. Fixed on both ends, and derived from
    # the seed data directly rather than hardcoded a second time here, so this list
    # can't drift out of sync with src/agentkit_mcp/data/seed.py's BUSINESS_KPIS again as domains
    # are added — "Forecasting"/"Anomalies" are cross-cutting categories there, not
    # real business domains, so they're excluded.
    try:
        from agentkit_mcp.data.seed import BUSINESS_KPIS as _BUSINESS_KPIS
        _RESOURCE_DOMAINS = tuple(
            d for d in _BUSINESS_KPIS if d not in ("Forecasting", "Anomalies")
        )
    except Exception:
        _RESOURCE_DOMAINS = ("Finance", "People", "Operations", "Customer", "Engineering")

    def _make_kpi_resource(domain: str):
        async def _read() -> Dict[str, Any]:
            return await query_kpis(domain=domain)
        return _read

    for _domain in _RESOURCE_DOMAINS:
        mcp.resource(
            f"kpi://{_domain}/latest",
            name=f"kpi_{_domain.lower()}_latest",
            description=f"Latest {_domain} KPI snapshot.",
            mime_type="application/json",
        )(_make_kpi_resource(_domain))

    @mcp.prompt(
        name="monthly_executive_briefing",
        description="Reusable prompt template for a monthly cross-domain executive briefing.",
    )
    def monthly_executive_briefing(month: str = "") -> str:
        period_clause = f" for {month}" if month else " for the most recent completed month"
        return (
            f"Produce a monthly executive briefing{period_clause}, covering every KPI domain "
            f"({', '.join(_RESOURCE_DOMAINS)}). For each domain: current value, trend vs. the "
            "prior period, and whether it crossed an anomaly threshold. Close with an overall "
            "company health score and the single most urgent issue to act on."
        )


def _serve_sse(port: int) -> None:
    """Serve SSE behind bearer-auth + rate-limit (gated by MCP_AUTH_TOKEN), composed with the
    read-only web facade (REST /api + SPA). MCP paths (/sse, /messages, /demo) keep the exact
    same middleware, auth and rate limit as before; everything else goes to the FastAPI facade.
    Falls back to the plain FastMCP runner if the ASGI app can't be wrapped on this version.
    """
    token = os.getenv("MCP_AUTH_TOKEN")
    if not token:
        raise RuntimeError("MCP_AUTH_TOKEN is strictly required for bearer token auth.")
    try:
        import uvicorn

        from agentkit_mcp.auth_middleware import BearerAuthRateLimit

        try:
            app = mcp.http_app(transport="sse")
        except TypeError:
            app = mcp.http_app()
        mcp_asgi = BearerAuthRateLimit(app)

        try:
            from agentkit_mcp.web_app import build_app

            api_asgi = build_app()
        except Exception as e:  # facade is additive — never block the MCP server on it
            log.warning("web facade unavailable (%s) — serving MCP only", e)
            api_asgi = None

        if api_asgi is None:
            composite = mcp_asgi
        else:
            _MCP_PREFIXES = ("/sse", "/messages", "/demo")

            async def composite(scope, receive, send):  # pure-ASGI dispatcher
                if scope["type"] == "lifespan":
                    # The FastMCP session manager owns the lifespan; the facade has no startup hooks.
                    return await mcp_asgi(scope, receive, send)
                path = scope.get("path", "")
                if scope["type"] == "http" and path.startswith(_MCP_PREFIXES):
                    return await mcp_asgi(scope, receive, send)
                return await api_asgi(scope, receive, send)

        log.info("Serving SSE (auth=%s) + web facade on :%s", bool(token), port)
        uvicorn.run(composite, host="0.0.0.0", port=port)
    except Exception as e:
        log.warning(
            "guarded SSE serve unavailable (%s) — falling back to mcp.run(sse)", e
        )
        mcp.run(transport="sse", host="0.0.0.0", port=port)


if __name__ == "__main__":
    if _FASTMCP:
        transport = os.getenv("MCP_TRANSPORT", "sse").lower()
        if transport == "stdio":
            # Local single-user IDE/desktop integration (Claude Desktop, Cursor, Devin —
            # all spawn this process directly via command+args and pipe stdin/stdout).
            # No network port, no MCP_AUTH_TOKEN: the OS process boundary is the security
            # boundary here, same as any other local stdio MCP server. show_banner=False
            # because stdout must carry nothing but JSON-RPC frames in this mode.
            log.info("Starting AgentKit MCP server (transport=stdio)...")
            mcp.run(transport="stdio", show_banner=False)
        else:
            port = int(os.getenv("MCP_PORT") or os.getenv("PORT") or "8005")
            log.info(
                "Starting AgentKit MCP server (transport=%s port=%s)...",
                transport,
                port,
            )
            _serve_sse(port)
    else:
        log.error("fastmcp not installed; cannot start MCP server. pip install fastmcp")
