"""Guardrail enforcement tests — the safety properties AgentKit claims must actually hold.

These assert *denials*, not just happy paths: a guardrail that has never been observed
refusing anything is an assumption, not a control.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agentkit_mcp.core.policy import (
    DESTRUCTIVE,
    READ,
    WRITE,  # noqa: E402
    PolicyEngine,
    ToolPolicy,
)


@pytest.fixture
def engine():
    return PolicyEngine()


@pytest.fixture
def clean_env(monkeypatch):
    """Guardrail state comes from env; start every test from a known-empty baseline."""
    for var in (
        "AGENTKIT_ALLOW_WRITES",
        "AGENTKIT_SCOPES",
        "AGENTKIT_APPROVAL_TOKEN",
        "AGENTKIT_AUDIT_LOG",
    ):
        monkeypatch.delenv(var, raising=False)
    return monkeypatch


def test_unknown_tool_is_denied(engine, clean_env):
    d = engine.check("not_a_real_tool")
    assert not d.allowed and "unknown_tool" in d.reason


def test_read_tools_allowed_by_default(engine, clean_env):
    engine.register(ToolPolicy(name="r", effect=READ))
    assert engine.check("r").allowed


def test_writes_denied_by_default_fails_closed(engine, clean_env):
    """The headline safety property: a default install cannot mutate anything."""
    engine.register(ToolPolicy(name="w", effect=WRITE))
    d = engine.check("w")
    assert not d.allowed and "writes_disabled" in d.reason


def test_writes_allowed_once_explicitly_enabled(engine, clean_env):
    clean_env.setenv("AGENTKIT_ALLOW_WRITES", "true")
    engine.register(ToolPolicy(name="w", effect=WRITE))
    assert engine.check("w").allowed


def test_missing_scope_is_denied(engine, clean_env):
    clean_env.setenv("AGENTKIT_ALLOW_WRITES", "true")
    clean_env.setenv("AGENTKIT_SCOPES", "other.scope")
    engine.register(ToolPolicy(name="w", effect=WRITE, scopes=("annotations.write",)))
    d = engine.check("w")
    assert not d.allowed and "missing_scope" in d.reason


def test_scope_granted_allows(engine, clean_env):
    clean_env.setenv("AGENTKIT_ALLOW_WRITES", "true")
    clean_env.setenv("AGENTKIT_SCOPES", "annotations.write,other")
    engine.register(ToolPolicy(name="w", effect=WRITE, scopes=("annotations.write",)))
    assert engine.check("w").allowed


def test_wildcard_scope_satisfies_any_requirement(engine, clean_env):
    clean_env.setenv("AGENTKIT_ALLOW_WRITES", "true")
    clean_env.setenv("AGENTKIT_SCOPES", "*")
    engine.register(ToolPolicy(name="w", effect=WRITE, scopes=("anything.at.all",)))
    assert engine.check("w").allowed


def test_destructive_requires_approval_token(engine, clean_env):
    clean_env.setenv("AGENTKIT_ALLOW_WRITES", "true")
    clean_env.setenv("AGENTKIT_SCOPES", "*")
    clean_env.setenv("AGENTKIT_APPROVAL_TOKEN", "human-held-secret")
    engine.register(ToolPolicy(name="d", effect=DESTRUCTIVE))

    assert not engine.check("d").allowed  # none supplied
    assert not engine.check("d", approval_token="guessed").allowed  # wrong one
    assert engine.check("d", approval_token="human-held-secret").allowed  # correct


def test_destructive_denied_when_no_approval_token_configured(engine, clean_env):
    """Fails closed: approval required but unconfigured must deny, never wave through."""
    clean_env.setenv("AGENTKIT_ALLOW_WRITES", "true")
    clean_env.setenv("AGENTKIT_SCOPES", "*")
    engine.register(ToolPolicy(name="d", effect=DESTRUCTIVE))
    d = engine.check("d", approval_token="anything")
    assert not d.allowed and "approval_unavailable" in d.reason


def test_dry_run_bypasses_approval_but_is_marked(engine, clean_env):
    """Previewing a destructive action is safe and must not need the human token —
    but the decision has to carry dry_run so the executor simulates instead of commits.
    """
    clean_env.setenv("AGENTKIT_ALLOW_WRITES", "true")
    clean_env.setenv("AGENTKIT_SCOPES", "*")
    engine.register(ToolPolicy(name="d", effect=DESTRUCTIVE))
    d = engine.check("d", dry_run=True)
    assert d.allowed and d.dry_run


def test_rate_limit_denies_beyond_window(engine, clean_env):
    engine.register(ToolPolicy(name="r", effect=READ, rate_limit=3, rate_window=60))
    assert all(engine.check("r").allowed for _ in range(3))
    d = engine.check("r")
    assert not d.allowed and "rate_limited" in d.reason


def test_audit_records_denials_with_reason(engine, clean_env):
    engine.register(ToolPolicy(name="w", effect=WRITE))
    d = engine.check("w")
    engine.record("w", d, args={"note": "x"}, caller="test")
    entries = engine.audit_log()
    assert len(entries) == 1
    assert entries[0]["allowed"] is False
    assert entries[0]["outcome"] == "denied"
    assert "writes_disabled" in entries[0]["reason"]


def test_audit_redacts_sensitive_arguments(engine, clean_env):
    engine.register(ToolPolicy(name="r", effect=READ))
    d = engine.check("r")
    engine.record(
        "r", d, args={"api_key": "sk-secret", "metric": "Revenue"}, caller="test"
    )
    digest = engine.audit_log()[0]["args_digest"]
    assert digest["api_key"] == "<redacted>"
    assert digest["metric"] == "Revenue"


def test_effect_must_be_valid():
    with pytest.raises(ValueError):
        ToolPolicy(name="bad", effect="sudo")
