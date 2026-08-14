"""Declarative tool-pack loading, validation and parameter binding.

These cover the properties that make a YAML-defined tool safe to expose to a model:
credentials stay in env vars, params are validated/coerced before they reach SQL, and a
malformed pack is rejected rather than silently half-registered.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from agentkit_mcp.toolpacks import (  # noqa: E402
    PackParam, load_pack_file, load_packs,
)


def _write(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "pack.yaml"
    p.write_text(body, encoding="utf-8")
    return p


def test_loads_bundled_annotations_pack():
    pack = load_pack_file(REPO / "packs" / "annotations.yaml")
    assert pack.name == "annotations"
    names = {t.name for t in pack.tools}
    assert names == {"list_annotations", "annotate_metric", "retract_annotation"}
    effects = {t.name: t.effect for t in pack.tools}
    assert effects["list_annotations"] == "read"
    assert effects["annotate_metric"] == "write"
    assert effects["retract_annotation"] == "destructive"


def test_datasource_url_comes_from_env_not_the_file(tmp_path, monkeypatch):
    """A pack file must be safe to commit — the URL is resolved from a named env var."""
    p = _write(tmp_path, """
name: t
datasource: {type: postgres, url_env: MY_DB_URL}
tools:
  - {name: a, description: d, query: "SELECT 1"}
""")
    pack = load_pack_file(p)
    monkeypatch.setenv("MY_DB_URL", "postgresql://example/db")
    assert pack.resolve_url() == "postgresql://example/db"


def test_missing_datasource_env_var_raises_actionable_error(tmp_path, monkeypatch):
    p = _write(tmp_path, """
name: t
datasource: {type: postgres, url_env: ABSENT_DB_URL}
tools:
  - {name: a, description: d, query: "SELECT 1"}
""")
    monkeypatch.delenv("ABSENT_DB_URL", raising=False)
    with pytest.raises(RuntimeError, match="ABSENT_DB_URL"):
        load_pack_file(p).resolve_url()


def test_invalid_effect_is_rejected(tmp_path):
    p = _write(tmp_path, """
name: t
datasource: {type: postgres, url_env: X}
tools:
  - {name: a, description: d, effect: sudo, query: "SELECT 1"}
""")
    with pytest.raises(ValueError, match="effect"):
        load_pack_file(p)


def test_read_tool_may_not_use_statement(tmp_path):
    """Guards against a mutating tool sneaking in mislabelled as read-only."""
    p = _write(tmp_path, """
name: t
datasource: {type: postgres, url_env: X}
tools:
  - {name: a, description: d, effect: read, statement: "DELETE FROM t"}
""")
    with pytest.raises(ValueError, match="effect=read"):
        load_pack_file(p)


def test_tool_without_query_statement_or_request_is_rejected(tmp_path):
    p = _write(tmp_path, """
name: t
datasource: {type: postgres, url_env: X}
tools:
  - {name: a, description: d}
""")
    with pytest.raises(ValueError, match="query"):
        load_pack_file(p)


def test_malformed_pack_is_skipped_not_fatal(tmp_path, monkeypatch):
    """One bad third-party pack must not stop the rest of the deployment serving."""
    (tmp_path / "bad.yaml").write_text("name: bad\ntools:\n  - {description: no name}\n")
    (tmp_path / "good.yaml").write_text(
        "name: good\ndatasource: {type: postgres, url_env: X}\n"
        "tools:\n  - {name: ok, description: d, query: 'SELECT 1'}\n"
    )
    monkeypatch.setenv("AGENTKIT_PACKS", str(tmp_path))
    packs = load_packs()
    assert "good" in packs and "bad" not in packs


def test_param_binding_coerces_and_defaults():
    from agentkit_mcp.toolpacks import PackTool
    tool = PackTool(
        name="t", description="d",
        params=[
            PackParam(name="n", type="integer", required=True),
            PackParam(name="limit", type="integer", default=50),
            PackParam(name="flag", type="boolean", default=False),
        ],
        query="SELECT 1",
    )
    bound = tool.bind({"n": "42", "flag": "true"})
    assert bound == {"n": 42, "limit": 50, "flag": True}


def test_missing_required_param_is_rejected():
    from agentkit_mcp.toolpacks import PackTool
    tool = PackTool(name="t", description="d",
                    params=[PackParam(name="n", type="integer", required=True)],
                    query="SELECT 1")
    with pytest.raises(ValueError, match="missing required parameter"):
        tool.bind({})


def test_unknown_param_is_rejected():
    """An arg the pack never declared must not silently reach the query."""
    from agentkit_mcp.toolpacks import PackTool
    tool = PackTool(name="t", description="d",
                    params=[PackParam(name="n", type="integer")], query="SELECT 1")
    with pytest.raises(ValueError, match="unknown parameter"):
        tool.bind({"n": 1, "injected": "DROP TABLE"})


def test_bad_type_is_rejected():
    from agentkit_mcp.toolpacks import PackTool
    tool = PackTool(name="t", description="d",
                    params=[PackParam(name="n", type="integer")], query="SELECT 1")
    with pytest.raises(ValueError, match="expects integer"):
        tool.bind({"n": "not-a-number"})
