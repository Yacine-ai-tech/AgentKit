"""Unit tests for the SSE bearer-auth + rate-limit ASGI middleware (pure, offline)."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agentkit_mcp.auth_middleware import BearerAuthRateLimit  # noqa: E402


def _run(mw, headers=None, ip="1.1.1.1"):
    scope = {"type": "http", "headers": headers or [], "client": (ip, 1)}
    sent = []

    async def receive():
        return {"type": "http.request", "body": b""}

    async def send(m):
        sent.append(m)

    asyncio.run(mw(scope, receive, send))
    return sent


def _dummy():
    calls = {"n": 0}

    async def app(scope, receive, send):
        calls["n"] += 1
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    return app, calls


def test_denies_without_token():
    app, calls = _dummy()
    mw = BearerAuthRateLimit(app, token="secret")
    sent = _run(mw, headers=[])
    assert sent[0]["status"] == 401 and calls["n"] == 0


def test_allows_with_correct_token():
    app, calls = _dummy()
    mw = BearerAuthRateLimit(app, token="secret")
    sent = _run(mw, headers=[(b"authorization", b"Bearer secret")])
    assert sent[0]["status"] == 200 and calls["n"] == 1


def test_rate_limit_429():
    app, calls = _dummy()
    # token="" (not None) explicitly disables auth for this test regardless of whatever
    # MCP_AUTH_TOKEN happens to be in the ambient environment — token=None falls back to
    # os.getenv("MCP_AUTH_TOKEN"), which made this test flaky (401 instead of 429) whenever
    # a real token was set/loaded from .env elsewhere in the test session.
    mw = BearerAuthRateLimit(app, token="", rate=3, window=60)
    for _ in range(3):
        _run(mw, ip="9.9.9.9")
    sent = _run(mw, ip="9.9.9.9")  # 4th request in window
    assert sent[0]["status"] == 429
    assert calls["n"] == 3  # only the first 3 reached the app


def test_health_bypasses_auth():
    app, calls = _dummy()
    mw = BearerAuthRateLimit(app, token="secret")
    scope = {"type": "http", "path": "/health", "headers": [], "client": ("1.2.3.4", 1)}
    sent = []

    async def recv():
        return {"type": "http.request", "body": b""}

    async def send(m):
        sent.append(m)

    asyncio.run(mw(scope, recv, send))
    assert (
        sent[0]["status"] == 200 and calls["n"] == 0
    )  # answered without auth, app not hit


def test_lifespan_passthrough():
    # non-http scopes (lifespan/websocket) must pass through untouched
    app, calls = _dummy()
    mw = BearerAuthRateLimit(app, token="secret")
    scope = {"type": "lifespan"}
    sent = []

    async def recv():
        return {"type": "lifespan.startup"}

    async def send(m):
        sent.append(m)

    asyncio.run(mw(scope, recv, send))
    assert calls["n"] == 1  # forwarded despite token set
