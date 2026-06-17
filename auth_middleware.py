"""Pure-ASGI bearer-token auth + per-client rate limiting for the AgentKit SSE endpoint.

Version-independent (doesn't depend on FastMCP internals): wraps any ASGI app. Gated by env:
  MCP_AUTH_TOKEN   — if set, requests must send `Authorization: Bearer <token>` (else 401).
  MCP_RATE_LIMIT   — max requests per window per client IP (default 120).
  MCP_RATE_WINDOW  — window seconds (default 60).
If MCP_AUTH_TOKEN is unset, auth is disabled (dev mode) and a warning should be logged by the
caller. Rate limiting always applies.
"""
from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from typing import Deque, Dict


# Small self-contained browser landing/demo page for the MCP server (served at /demo, before
# auth). A browser can't speak MCP, so this shows liveness, the tool catalog, and how to connect.
_DEMO_HTML = b"""<!DOCTYPE html><html lang=en><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1"><title>AgentKit - MCP server</title>
<style>:root{--bg:#0d1117;--card:#161b22;--bd:#30363d;--tx:#e6edf3;--mut:#8b949e;--ac:#10b981}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--tx);font:15px/1.55 system-ui,Segoe UI,Roboto,sans-serif}
.wrap{max-width:760px;margin:0 auto;padding:32px 20px 64px}h1{font-size:1.6rem;margin:0 0 4px}
.sub{color:var(--mut);margin:0 0 22px}.card{background:var(--card);border:1px solid var(--bd);border-radius:12px;padding:20px;margin-bottom:18px}
.pill{display:inline-block;font-size:.72rem;padding:2px 8px;border-radius:999px;background:#1f2937;color:var(--mut);margin-left:8px}
.pill.ok{background:#0f2e1b;color:var(--ac)}code,pre{background:#0d1117;border:1px solid var(--bd);border-radius:6px}
code{padding:1px 6px;color:var(--mut)}pre{padding:14px;overflow:auto;white-space:pre-wrap}
.tools{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:8px;margin-top:8px}
.tool{background:#0d1117;border:1px solid var(--bd);border-radius:8px;padding:8px 10px;font-size:.85rem}
.tool b{color:var(--ac)}a{color:var(--ac)}</style></head><body><div class=wrap>
<h1>AgentKit <span id=h class=pill>checking...</span></h1>
<p class=sub>Production <b>MCP server</b> exposing your business KPIs as agent tools (bearer-auth + rate-limited SSE).</p>
<div class=card><b>Connect an MCP client</b> (Claude Desktop, <code>mcp</code> CLI, or any agent) to the SSE endpoint:
<pre>URL:    &lt;this-host&gt;/sse
Header: Authorization: Bearer &lt;MCP_AUTH_TOKEN&gt;</pre>
A browser can't speak MCP - point your agent at the URL above.</div>
<div class=card><b>Tools available</b><div class=tools>
<div class=tool><b>query_kpis</b><br>filter KPIs by domain</div>
<div class=tool><b>get_company_health</b><br>overall health index</div>
<div class=tool><b>detect_kpi_anomalies</b><br>flag outliers</div>
<div class=tool><b>forecast_metric</b><br>project a metric forward</div>
<div class=tool><b>list_available_metrics</b><br>metric catalog</div>
<div class=tool><b>get_executive_summary</b><br>board-ready summary</div>
<div class=tool><b>monthly_briefing</b><br>composed monthly brief</div>
<div class=tool><b>finance / growth / ops /<br>people / esg / itops_latest</b><br>latest per domain</div>
</div></div>
<p class=sub>Health: <a href=/health>/health</a></p></div>
<script>fetch('/health').then(r=>r.json()).then(j=>{var e=document.getElementById('h');e.textContent=j.status||'ok';e.className='pill ok'}).catch(()=>{document.getElementById('h').textContent='offline'})</script>
</body></html>"""


class BearerAuthRateLimit:
    def __init__(self, app, token: str | None = None, rate: int = 120, window: int = 60):
        self.app = app
        self.token = token if token is not None else os.getenv("MCP_AUTH_TOKEN")
        self.rate = int(os.getenv("MCP_RATE_LIMIT", rate))
        self.window = int(os.getenv("MCP_RATE_WINDOW", window))
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            return await self.app(scope, receive, send)

        # Liveness probe — answer /health directly (before auth) so MCP/SSE servers are
        # health-checkable by Docker/orchestrators even though MCP itself serves /sse.
        if scope.get("path") == "/health":
            body = b'{"status":"ok","service":"agentkit"}'
            await send({"type": "http.response.start", "status": 200,
                        "headers": [(b"content-type", b"application/json"),
                                    (b"content-length", str(len(body)).encode())]})
            await send({"type": "http.response.body", "body": body})
            return

        # Browser landing/demo page — served before auth (a browser can't speak MCP).
        if scope.get("path") in ("/demo", "/demo/"):
            await send({"type": "http.response.start", "status": 200,
                        "headers": [(b"content-type", b"text/html; charset=utf-8"),
                                    (b"content-length", str(len(_DEMO_HTML)).encode())]})
            await send({"type": "http.response.body", "body": _DEMO_HTML})
            return

        headers = {k.lower(): v for k, v in (scope.get("headers") or [])}

        # 1) auth
        if self.token:
            auth = headers.get(b"authorization", b"").decode()
            if auth != f"Bearer {self.token}":
                return await self._deny(send, 401, "unauthorized")

        # 2) rate limit per client IP (sliding window)
        ip = (scope.get("client") or ("unknown",))[0]
        now = time.monotonic()
        q = self._hits[ip]
        while q and now - q[0] > self.window:
            q.popleft()
        if len(q) >= self.rate:
            return await self._deny(send, 429, "rate limit exceeded")
        q.append(now)

        return await self.app(scope, receive, send)

    @staticmethod
    async def _deny(send, code: int, msg: str):
        body = msg.encode()
        await send({"type": "http.response.start", "status": code,
                    "headers": [(b"content-type", b"text/plain"),
                                (b"content-length", str(len(body)).encode())]})
        await send({"type": "http.response.body", "body": body})
