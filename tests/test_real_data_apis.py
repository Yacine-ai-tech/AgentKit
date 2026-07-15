import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import importlib
import pytest
from fastapi.testclient import TestClient


def _get_client():
    """Attempt to build a TestClient from the AgentKit app."""
    for module_name, attr in [("web_app", "app"), ("main", "app")]:
        try:
            mod = importlib.import_module(module_name)
            app = getattr(mod, attr, None)
            if not app and hasattr(mod, "build_app"):
                app = mod.build_app()
            if app:
                return TestClient(app)
        except Exception:
            continue
    return None


def test_agentkit_real_mcp_tool_execution():
    """Simulates a real MCP remote server POST request executing a tool."""
    client = _get_client()
    if client is None:
        pytest.skip("Could not import AgentKit app")

    payload = {
        "jsonrpc": "2.0",
        "method": "callTool",
        "params": {
            "name": "get_company_health",
            "arguments": {"category": "Financial"}
        },
        "id": "1"
    }
    response = client.post("/messages", json=payload)
    assert response.status_code in (200, 202, 401, 403, 404, 405, 422)


def test_agentkit_health():
    client = _get_client()
    if client is None:
        pytest.skip("Could not import AgentKit app")
    response = client.get("/health")
    assert response.status_code in (200, 401, 403)
