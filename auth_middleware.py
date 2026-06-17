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
