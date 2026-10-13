import importlib

import pytest


@pytest.fixture
def tele(monkeypatch):
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    for k in ("TELEMETRY_OPT_OUT", "DO_NOT_TRACK", "TELEMETRY_URL"):
        monkeypatch.delenv(k, raising=False)
    import agentkit_mcp.telemetry as t

    importlib.reload(t)
    posted = []
    import httpx

    monkeypatch.setattr(httpx, "post", lambda url, **kw: posted.append((url, kw.get("json"))))
    monkeypatch.setattr(t, "_logs_dir", lambda: __import__("tempfile").mkdtemp())
    return t, posted


def test_default_destination_when_url_empty(tele, monkeypatch):
    t, posted = tele
    monkeypatch.setenv("TELEMETRY_URL", "")
    t._send()
    assert posted and posted[0][0] == t.DEFAULT_TELEMETRY_URL
    assert posted[0][1]["service"] == "AgentKit" and posted[0][1]["event"] == "startup"


def test_opt_out_flags_send_nothing(tele, monkeypatch):
    t, posted = tele
    monkeypatch.setenv("TELEMETRY_OPT_OUT", "true")
    t._send()
    monkeypatch.delenv("TELEMETRY_OPT_OUT")
    monkeypatch.setenv("DO_NOT_TRACK", "1")
    t._send()
    assert posted == []
