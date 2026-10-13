"""REST facade behaviour for pack tools: input problems are 4xx, not 200 with an error body."""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(monkeypatch):
    from agentkit_mcp.web_app import build_app

    monkeypatch.setenv("REQUIRE_INTERNAL_TOKEN", "false")
    monkeypatch.setenv("AGENTKIT_ALLOW_WRITES", "true")
    monkeypatch.setenv("AGENTKIT_SCOPES", "annotations.write")
    return TestClient(build_app())


def test_missing_required_parameter_is_422(client):
    # annotate_metric needs a note; the facade fills metric/period defaults but not note.
    r = client.post("/api/packs/annotations/annotate_metric", json={"metric": "ARR"})
    assert r.status_code == 422, r.text
    assert "note" in r.json()["detail"]


def test_unknown_pack_is_404(client):
    r = client.post("/api/packs/nope/none", json={})
    assert r.status_code == 404
    assert r.json()["detail"] == "unknown pack: nope"


def test_workflow_requires_a_question(client):
    r = client.post("/api/workflow/run", json={})
    assert r.status_code == 400
    assert r.json()["detail"] == "question required"


def test_observability_is_scoped_to_the_callers_session(client):
    client.get("/api/kpis", headers={"X-Demo-Session-Id": "session-a"})
    own = client.get("/api/observability", headers={"X-Demo-Session-Id": "session-a"}).json()["requests"]
    other = client.get("/api/observability", headers={"X-Demo-Session-Id": "session-b"}).json()["requests"]
    anonymous = client.get("/api/observability").json()["requests"]
    assert any(r["path"] == "/api/kpis" for r in own)
    assert not any(r["path"] == "/api/kpis" for r in other)
    assert anonymous == []


def test_annotation_statements_are_scoped_to_the_writing_session():
    from agentkit_mcp.toolpacks import load_pack_file as load_pack
    import pathlib

    pack = load_pack(pathlib.Path(__file__).resolve().parent.parent / "packs" / "annotations.yaml")
    tools = {t.name: t for t in pack.tools}
    assert "%(_session)s" in tools["list_annotations"].query
    assert "owner_session_id" in tools["annotate_metric"].statement
    assert "%(_session)s" in tools["annotate_metric"].statement
    assert "owner_session_id" in tools["retract_annotation"].statement
