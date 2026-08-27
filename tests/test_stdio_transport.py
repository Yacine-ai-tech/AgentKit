"""Real end-to-end test of MCP_TRANSPORT=stdio — spawns the actual entrypoint as a
subprocess (exactly how Claude Desktop/Cursor/Devin do via claude_desktop_config.json /
cursor_mcp.json / devin_mcp.json) and speaks real JSON-RPC 2.0 over its stdin/stdout.

Regression guard for two real bugs found in production use: (1) MCP_TRANSPORT was
previously never read anywhere — the server always started an SSE/HTTP server
regardless, so every "stdio" client config silently failed; (2) log lines went to
stdout, which would have corrupted the JSON-RPC stream even after (1) was fixed.
No Postgres needed — this only exercises protocol-level requests (initialize,
tools/list), not tool execution against real data.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"


def _read_json_line(proc: subprocess.Popen, timeout: float = 15.0) -> dict:
    """Read one line from the subprocess's stdout and parse it as JSON, with a
    hard timeout so a regression hangs the test instead of the whole suite."""
    import selectors

    sel = selectors.DefaultSelector()
    sel.register(proc.stdout, selectors.EVENT_READ)
    if not sel.select(timeout=timeout):
        raise TimeoutError(
            f"no stdout line within {timeout}s (transport likely broken)"
        )
    line = proc.stdout.readline()
    assert line, "stdout closed with no data — process likely crashed, check stderr"
    return json.loads(line)


@pytest.fixture
def stdio_server():
    env = os.environ.copy()
    env["MCP_TRANSPORT"] = "stdio"
    env["PYTHONPATH"] = str(SRC_DIR)
    proc = subprocess.Popen(
        [sys.executable, "-u", "-m", "agentkit_mcp.mcp_server"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        cwd=str(REPO_ROOT),
        env=env,
    )
    try:
        yield proc
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def test_stdio_initialize_handshake(stdio_server):
    proc = stdio_server
    req = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "pytest", "version": "1.0"},
        },
    }
    proc.stdin.write(json.dumps(req) + "\n")
    proc.stdin.flush()

    resp = _read_json_line(proc)
    assert resp["id"] == 1
    assert resp["result"]["serverInfo"]["name"] == "AgentKit Business Intelligence"
    assert "tools" in resp["result"]["capabilities"]


def test_stdio_tools_list_matches_real_registry(stdio_server):
    proc = stdio_server
    init = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "pytest", "version": "1.0"},
        },
    }
    proc.stdin.write(json.dumps(init) + "\n")
    proc.stdin.write(
        json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n"
    )
    proc.stdin.flush()
    _read_json_line(proc)  # initialize response

    proc.stdin.write(
        json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}) + "\n"
    )
    proc.stdin.flush()
    resp = _read_json_line(proc)

    names = {t["name"] for t in resp["result"]["tools"]}
    # Subset, not equality: declarative tool packs (AGENTKIT_PACKS) add tools on top of
    # the built-ins, so the exact set is deployment-dependent. The invariant that
    # matters here is that the six native tools are always advertised over stdio.
    assert {
        "query_kpis",
        "get_company_health",
        "detect_kpi_anomalies",
        "forecast_metric",
        "list_available_metrics",
        "get_executive_summary",
    } <= names
