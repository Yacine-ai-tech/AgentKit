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
