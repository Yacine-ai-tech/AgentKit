"""The documented `agentkit-mcp` command must exist and be wired to a callable."""
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_console_script_is_declared():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    assert project["scripts"]["agentkit-mcp"] == "agentkit_mcp.mcp_server:main"


def test_main_is_importable_and_callable():
    from agentkit_mcp.mcp_server import main
    assert callable(main)


def test_registry_metadata_matches_the_package_version():
    import json
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    server = json.loads((ROOT / "server.json").read_text())
    assert server["version"] == project["version"]
    assert server["packages"][0]["identifier"] == project["name"]
    assert server["packages"][0]["version"] == project["version"]
    assert len(server["description"]) <= 100
    assert "mcp-name: " + server["name"] in (ROOT / "README.md").read_text()
