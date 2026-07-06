# GAP_REPORT — AgentKit (redesign v2 — 2026-07-06)

## 1. Inventory (verified)

- **No REST API, no frontend.** FastMCP server (`mcp_server.py`): 6 tools, 6 `kpi://` resources,
  1 prompt. Deployed on Render as SSE (`MCP_TRANSPORT=sse`), wrapped by `BearerAuthRateLimit`
  (auth_middleware.py) which serves `/health` and a `/demo` landing page BEFORE auth and gates
  everything else (incl. `/sse`, `/messages`) with `MCP_AUTH_TOKEN` + rate limit.
- Tools are plain async functions calling `services/` (pg_store / insights / forecasting) over
  Neon Postgres. Signatures: `query_kpis(domain?, period_from?, period_to?, metric_filter?, limit)`,
  `get_company_health(domain?)`, `detect_kpi_anomalies(domain, method="zscore", threshold=2.5)`,
  `forecast_metric(metric_name, periods=6, confidence_level=0.95)`,
  `list_available_metrics(domain?)`, `get_executive_summary()`. Without `POSTGRES_URL` the
  tools RAISE ("data layer unavailable") — never fabricate.
- `workflow.py`: real LangGraph pipeline `planner_agent → analyst_agent → reporter_agent`
  (`analyze(question)`). `demos/`: CrewAI + Claude-Agent-SDK scripts. `logs/` has no committed
  run log → Workflow page shows the real structure; no fake replay.
- `claude_desktop_config.example.json`: local-stdio + remote-SSE (via mcp-remote) entries.
  ⚠ remote URL points at the retired `*.ysiddo-ai-projects.app` domain → updated to the
  Render URL as part of this change (doc fix).

## 2. The approved extension (SPEC §2): read-only REST facade + SPA, zero logic duplication

New `web_app.py` (FastAPI) exposing the SAME functions the MCP tools call:

```
GET /health                    (same public shape the middleware served)
GET /api/tools                 static metadata mirroring the six real signatures
GET /api/kpis?domain&period_from&period_to&metric_filter&limit
GET /api/health-score?domain
GET /api/anomalies?domain&method&threshold
GET /api/forecast?metric&periods&confidence_level
GET /api/metrics?domain
GET /api/summary
+ SPA serving (frontend/dist)
```

`mcp_server._serve_sse` becomes a pure-ASGI composite dispatcher:
- `lifespan` → MCP app (session manager) — middleware passes non-http scopes through.
- `/sse*`, `/messages*`, `/demo*` → `BearerAuthRateLimit(mcp.http_app())` — **unchanged**:
  same auth, same rate limit, same paths, Claude Desktop clients unaffected.
- everything else (`/health`, `/api/*`, SPA) → the FastAPI facade (public, read-only; the
  KPI data is the seeded demo-company dataset, consistent with the rest of the portfolio).
- stdio transport path untouched.

Tool errors (no DB) surface as HTTP 503 with the real message — the UI shows an honest
"data layer unavailable" state.

## 3. Real-vs-Demo

| Screen | Source |
|---|---|
| Overview (summary + health) | real /api/summary, /api/health-score |
| MCP Tools Center + try-it | real /api/* execution per tool |
| Business Intelligence | real /api/kpis + /api/metrics + /api/anomalies + /api/forecast |
| Workflow | factual structure from workflow.py (LangGraph, 3 agents); no fake replay/run |
| Connect | real config example + live Render URL + real demos/ scripts referenced |
| Resources & Prompts | factual list (6 resources, 1 prompt with its real text) |
