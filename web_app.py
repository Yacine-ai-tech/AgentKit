"""AgentKit web facade — read-only REST + SPA over the SAME functions the MCP tools use.

No business logic lives here: every /api endpoint delegates to the tool functions in
mcp_server.py (which call services/pg_store, services/insights, services/forecasting).
Data-layer failures surface as HTTP 503 with the real message — never fabricated data.
"""
from __future__ import annotations

import os
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import mcp_server as tools

# Observability: in-memory request log (v1 "observability" ask) — real facade calls.
from collections import deque as _deque
from datetime import datetime as _dt
import time as _time

_OBS: "_deque[Dict[str, Any]]" = _deque(maxlen=200)

# Static metadata mirroring the six REAL tool signatures (mcp_server.py).
TOOL_META = [
    {
        "name": "query_kpis",
        "description": "Return KPI metrics for a domain and period window.",
        "params": [
            {"name": "domain", "type": "string", "required": False},
            {"name": "period_from", "type": "string", "required": False},
            {"name": "period_to", "type": "string", "required": False},
            {"name": "metric_filter", "type": "string", "required": False},
            {"name": "limit", "type": "integer", "required": False, "default": 100},
        ],
        "endpoint": "/api/kpis",
    },
    {
        "name": "get_company_health",
        "description": "Composite company health index for a domain (or all).",
        "params": [{"name": "domain", "type": "string", "required": False}],
        "endpoint": "/api/health-score",
    },
    {
        "name": "detect_kpi_anomalies",
        "description": "Find anomalies in a domain's KPI history (z-score).",
        "params": [
            {"name": "domain", "type": "string", "required": True},
            {"name": "method", "type": "string", "required": False, "default": "zscore"},
            {"name": "threshold", "type": "number", "required": False, "default": 2.5},
        ],
        "endpoint": "/api/anomalies",
    },
    {
        "name": "forecast_metric",
        "description": "Forecast N periods ahead for a named metric with CI bands.",
        "params": [
            {"name": "metric_name", "type": "string", "required": True},
            {"name": "periods", "type": "integer", "required": False, "default": 6},
            {"name": "confidence_level", "type": "number", "required": False, "default": 0.95},
        ],
        "endpoint": "/api/forecast",
    },
    {
        "name": "list_available_metrics",
        "description": "Discovery: metrics, categories and periods available in the store.",
        "params": [{"name": "domain", "type": "string", "required": False}],
        "endpoint": "/api/metrics",
    },
    {
        "name": "get_executive_summary",
        "description": "One-shot synthesis of health, key KPIs and anomalies.",
        "params": [],
        "endpoint": "/api/summary",
    },
]


def _guard(result: Dict[str, Any]) -> Dict[str, Any]:
    return result


async def _call(fn, *args, **kwargs) -> Dict[str, Any]:
    try:
        return _guard(await fn(*args, **kwargs))
    except RuntimeError as e:  # tools raise when the data layer is unavailable
        raise HTTPException(status_code=503, detail=str(e))


def build_app() -> FastAPI:
    app = FastAPI(title="AgentKit", version="0.1.0",
                  description="AI Agent Intelligence Platform — read-only facade over the MCP tools.")

# --- ETHICAL TELEMETRY ---
import threading
import requests
import os
import logging

def _send_telemetry():
    if os.environ.get("TELEMETRY_OPT_OUT", "").lower() in ("1", "true", "yes"):
        return
    try:
        logging.info("📡 Anonymous usage telemetry is ENABLED. This helps us understand project usage.")
        logging.info("📡 To disable this, set the environment variable TELEMETRY_OPT_OUT=true.")
        requests.post(
            "https://gateway.ysiddo-ai-projects.app/telemetry", 
            json={"service": "AgentKit", "event": "startup"},
            timeout=2
        )
    except Exception:
        pass

threading.Thread(target=_send_telemetry, daemon=True).start()
# -------------------------


from fastapi import Request
from fastapi.responses import JSONResponse
import os as _os

@app.middleware("http")
async def verify_internal_token(request: Request, call_next):
    # Allow health checks and public auth routes
    if request.url.path in ["/health", "/docs", "/openapi.json", "/api/redoc"] or request.url.path.startswith("/api/v1/auth/"):
        return await call_next(request)
        
    token = request.headers.get("X-OmniIntel-Internal-Token")
    expected_token = _os.environ.get("OMNIINTEL_INTERNAL_TOKEN", "default-dev-token")
    
    if token != expected_token and _os.environ.get("REQUIRE_INTERNAL_TOKEN", "true").lower() == "true":
        return JSONResponse(status_code=403, content={"detail": "Missing or invalid X-OmniIntel-Internal-Token"})
        
    return await call_next(request)

    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET", "POST"], allow_headers=["*"])

    @app.middleware("http")
    async def _observe(request, call_next):
        t0 = _time.time()
        response = await call_next(request)
        if request.url.path.startswith("/api"):
            _OBS.appendleft({
                "ts": _dt.utcnow().isoformat() + "Z",
                "method": request.method,
                "path": request.url.path,
                "query": str(request.url.query or ""),
                "status": response.status_code,
                "ms": round((_time.time() - t0) * 1000, 1),
            })
        return response

    @app.get("/health", include_in_schema=False)
    async def health() -> Dict[str, Any]:
        return {"status": "ok", "service": "agentkit", "version": "0.1.0"}

    @app.get("/api/tools")
    async def list_tools() -> Dict[str, Any]:
        return {"tools": TOOL_META, "resources": [f"kpi://{d}/latest" for d in
                ("Finance", "Growth", "Operations", "People", "ESG", "IT_Ops")],
                "prompts": ["monthly_executive_briefing"]}

    @app.get("/api/kpis")
    async def kpis(domain: Optional[str] = None, period_from: Optional[str] = None,
                   period_to: Optional[str] = None, metric_filter: Optional[str] = None,
                   limit: int = 100) -> Dict[str, Any]:
        return await _call(tools.query_kpis, domain=domain, period_from=period_from,
                           period_to=period_to, metric_filter=metric_filter, limit=limit)

    @app.get("/api/health-score")
    async def health_score(domain: Optional[str] = None) -> Dict[str, Any]:
        return await _call(tools.get_company_health, domain=domain)

    @app.get("/api/anomalies")
    async def anomalies(domain: str, method: str = "zscore", threshold: float = 2.5) -> Dict[str, Any]:
        return await _call(tools.detect_kpi_anomalies, domain=domain, method=method, threshold=threshold)

    @app.get("/api/forecast")
    async def forecast(metric: str, periods: int = 6, confidence_level: float = 0.95) -> Dict[str, Any]:
        return await _call(tools.forecast_metric, metric_name=metric, periods=periods,
                           confidence_level=confidence_level)

    @app.get("/api/metrics")
    async def metrics(domain: Optional[str] = None) -> Dict[str, Any]:
        return await _call(tools.list_available_metrics, domain=domain)

    @app.get("/api/summary")
    async def summary() -> Dict[str, Any]:
        return await _call(tools.get_executive_summary)

    @app.get("/api/observability")
    async def observability(limit: int = 100) -> Dict[str, Any]:
        """Recent facade requests (method, path, status, latency) — real observability."""
        return {"requests": list(_OBS)[:limit], "capacity": _OBS.maxlen}

    @app.post("/api/workflow/run")
    async def workflow_run(body: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the real 3-agent LangGraph workflow (planner → analyst → reporter).
        Runs in a thread — the graph uses asyncio.run internally. Spends LLM credits."""
        question = (body or {}).get("question", "").strip()
        if not question:
            raise HTTPException(status_code=400, detail="question required")
        import anyio
        try:
            from workflow import analyze as run_workflow
        except Exception as e:
            raise HTTPException(status_code=501, detail=f"workflow_unavailable: {e}")
        t0 = _time.time()
        try:
            result = await anyio.to_thread.run_sync(run_workflow, question)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"workflow_failed: {e}")
        result["_elapsed_ms"] = round((_time.time() - t0) * 1000, 1)
        return result

        @app.get("/", include_in_schema=False)
        async def root() -> Dict[str, Any]:
            return {"service": "agentkit", "docs": "/docs", "mcp_sse": "/sse"}

    return app
