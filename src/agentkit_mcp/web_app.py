"""AgentKit web facade — read-only REST + SPA over the SAME functions the MCP tools use.

No business logic lives here: every /api endpoint delegates to the tool functions in
mcp_server.py (which call services/pg_store, services/insights, services/forecasting).
Data-layer failures surface as HTTP 503 with the real message — never fabricated data.
"""
from __future__ import annotations

import os
from typing import Any, Dict, Optional

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from agentkit_mcp import mcp_server as tools

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

    from fastapi import Request
    from fastapi.responses import JSONResponse
    import os as _os

    @app.middleware("http")
    async def verify_internal_token(request: Request, call_next):
        # Allow health checks, public auth routes, and frontend static assets
        if request.method == "OPTIONS" or request.url.path in ["/", "/health", "/docs", "/openapi.json", "/api/redoc", "/favicon.png", "/favicon.ico", "/mark.png", "/logo.png"] or request.url.path.startswith("/api/v1/auth/") or request.url.path.startswith("/assets/") or request.url.path.startswith("/static/"):
            return await call_next(request)

        token = request.headers.get("X-OmniIntel-Internal-Token")
        valid_tokens = {_os.environ.get("OMNIINTEL_INTERNAL_TOKEN")}
        valid_tokens.discard(None)

        auth_disabled = _os.environ.get("ALLOW_UNAUTHENTICATED_API", "false").lower() == "true"
        if token not in valid_tokens and not auth_disabled:
            return JSONResponse(status_code=403, content={"detail": "Missing or invalid X-OmniIntel-Internal-Token"})

        return await call_next(request)

    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET", "POST"], allow_headers=["*"])

    try:
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        assets_dir = os.path.join(root_dir, "frontend", "dist", "assets")
        if os.path.exists(assets_dir):
            app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
    except Exception as e:
        import logging
        logging.warning("assets mount failed: %s", e)

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
        """Discovery endpoint: returns all registered tools, resources, and prompts.
        Consumers should call this once and cache; add a tool/resource/prompt to the
        server and every connected consumer sees it on their next discovery refresh.
        """
        from agentkit_mcp import mcp_server as _mcp_mod

        dynamic_tools = []
        for p in getattr(tools, "PACKS", {}).values():
            for t in p.tools:
                meta = t.to_meta()
                meta["endpoint"] = f"/api/packs/{p.name}/{t.name}"
                dynamic_tools.append(meta)

        # Discover live resources and prompts from the FastMCP server
        resources_out: list = []
        prompts_out:   list = []
        try:
            # Optimize: Avoid full Client initialization on every request
            raw_resources = []
            if hasattr(_mcp_mod.mcp, "_resources"):
                raw_resources = list(_mcp_mod.mcp._resources.values())
            raw_prompts = []
            if hasattr(_mcp_mod.mcp, "_prompts"):
                raw_prompts = list(_mcp_mod.mcp._prompts.values())

            resources_out = [
                {"uri": str(r.uri), "name": r.name or str(r.uri), "description": r.description or ""}
                for r in raw_resources
            ]
            prompts_out = [
                {
                    "name": p.name,
                    "description": p.description or "",
                    "arguments": [
                        {"name": a.name, "description": a.description or "", "required": a.required}
                        for a in (p.arguments or [])
                    ],
                }
                for p in raw_prompts
            ]
        except Exception as _e:
            import logging as _logging
            _logging.getLogger(__name__).debug("resource/prompt listing failed: %s", _e)

        return {
            "tools":     TOOL_META + dynamic_tools,
            "resources": resources_out,
            "prompts":   prompts_out,
        }

    @app.get("/api/resources")
    async def read_resource(uri: str) -> Dict[str, Any]:
        """Fetch a single MCP resource by URI.
        Consumers (e.g. a voice agent) call this to pin live data into their context.
        Returns {"uri", "content", "mime_type"} or {"error": ...} on failure.
        """
        from agentkit_mcp import mcp_server as _mcp_mod
        try:
            # Bypass Client overhead
            func = _mcp_mod.mcp._resources.get(uri)
            if not func:
                return {"error": "not found", "uri": uri}
            import inspect
            if inspect.iscoroutinefunction(func):
                result = await func()
            else:
                result = func()

            # result is a list of content parts or single string; join text parts
            content_parts = []
            if isinstance(result, str):
                content_parts.append(result)
            else:
                for part in (result or []):
                    content_parts.append(part.text if hasattr(part, "text") else str(part))
            return {"uri": uri, "content": "\n".join(content_parts), "mime_type": "text/plain"}
        except Exception as exc:
            return {"error": str(exc), "uri": uri}

    @app.get("/api/prompts/{name}")
    async def render_prompt(name: str, request: Request) -> Dict[str, Any]:
        """Render a named MCP prompt template, optionally with arguments passed as query params.
        Returns {"name", "content"} where content is the rendered prompt string.
        """
        from agentkit_mcp import mcp_server as _mcp_mod
        args = {k: v for k, v in request.query_params.items()}
        try:
            func = _mcp_mod.mcp._prompts.get(name)
            if not func:
                return {"error": "not found", "name": name}

            import inspect
            if inspect.iscoroutinefunction(func):
                result = await func(**args)
            else:
                result = func(**args)

            # result is a string or list of PromptMessage; join text content
            parts = []
            if isinstance(result, str):
                parts.append(result)
            else:
                for msg in (result or []):
                    content = getattr(msg, "content", msg)
                    if hasattr(content, "text"):
                        parts.append(content.text)
                    else:
                        parts.append(str(content))
            return {"name": name, "content": "\n".join(parts)}
        except Exception as exc:
            return {"error": str(exc), "name": name}

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

    # ── Capability / guardrail surface ──────────────────────────────────────
    @app.get("/api/policy")
    async def policy() -> Dict[str, Any]:
        """Declared capability envelope: every tool's effect class, required scopes,
        rate limit and approval requirement, plus the global switches. This is the
        endpoint to read (or diff in CI) to answer "what can this agent actually do?"."""
        from agentkit_mcp.core.policy import policy_engine
        return policy_engine.describe()

    @app.get("/api/audit")
    async def audit(
        limit: int = 100,
        effect: Optional[str] = None,
        x_demo_session_id: Optional[str] = Header(default=None, alias="X-Demo-Session-Id"),
    ) -> Dict[str, Any]:
        """Audit trail of tool invocations — allowed and denied, with the deny reason.

        Denials are recorded too: "the agent tried to do X and was blocked" is exactly
        the event an operator needs to see. Scoped to entries with no visitor session of
        their own (MCP/CLI calls) plus this caller's own REST calls, never another
        visitor's — see PolicyEngine.audit_log.
        """
        from agentkit_mcp.core.policy import policy_engine
        return {"entries": policy_engine.audit_log(limit=limit, effect=effect, session_id=x_demo_session_id)}

    @app.get("/api/llm-routing")
    async def llm_routing() -> Dict[str, Any]:
        """Which model each tier resolves to and whether inference is local or hosted.
        Never returns key material — only whether a key is present."""
        from agentkit_mcp.core.llm_router import describe_routing
        return describe_routing()

    @app.get("/api/packs")
    async def list_packs() -> Dict[str, Any]:
        """Loaded declarative tool packs and the tools each contributes."""
        return {
            "packs": [
                {
                    "name": p.name,
                    "description": p.description,
                    "datasource_type": p.datasource_type,
                    "source_file": os.path.basename(p.source_file or ""),
                    "tools": [t.to_meta() for t in p.tools],
                }
                for p in getattr(tools, "PACKS", {}).values()
            ]
        }

    @app.post("/api/packs/{pack_name}/{tool_name}")
    async def run_pack_tool(
        pack_name: str,
        tool_name: str,
        body: Dict[str, Any],
        x_demo_session_id: Optional[str] = Header(default=None, alias="X-Demo-Session-Id"),
    ) -> Dict[str, Any]:
        """Invoke a declarative pack tool through the same policy path the MCP tools use.

        POST (not GET) because a pack tool may mutate; the effect class in /api/policy
        says which. Body is the tool's params, plus optional dry_run / approval_token.
        """
        from agentkit_mcp.core.policy import PolicyDenied
        from agentkit_mcp.pack_runtime import call_pack_tool

        pack = getattr(tools, "PACKS", {}).get(pack_name)
        if pack is None:
            raise HTTPException(status_code=404, detail=f"unknown pack: {pack_name}")
        tool = next((t for t in pack.tools if t.name == tool_name), None)
        if tool is None:
            raise HTTPException(status_code=404, detail=f"unknown tool: {tool_name}")
        try:
            return await call_pack_tool(pack, tool, body or {}, caller="rest", session_id=x_demo_session_id)
        except PolicyDenied as e:
            # 403 with the actual reason — a guardrail that blocks silently is not one.
            raise HTTPException(status_code=403, detail=str(e))

    @app.post("/api/workflow/run")
    async def workflow_run(body: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the real 3-agent LangGraph workflow (planner → analyst → reporter).
        Runs in a thread — the graph uses asyncio.run internally. Spends LLM credits."""
        question = (body or {}).get("question", "").strip()
        if not question:
            raise HTTPException(status_code=400, detail="question required")
        import anyio
        try:
            from agentkit_mcp.workflow import analyze as run_workflow
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
    async def root():
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        spa = os.path.join(root_dir, "frontend", "dist", "index.html")
        if os.path.exists(spa):
            return FileResponse(spa)
        return {"service": "agentkit", "docs": "/docs", "mcp_sse": "/sse"}

    return app
