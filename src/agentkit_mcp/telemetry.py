"""Anonymous startup ping, shared by the REST facade and the MCP console entry point.

On by default. Sent to ``TELEMETRY_URL`` when that is set to a non-empty value, otherwise to the
project's collector. Disabled by ``TELEMETRY_OPT_OUT=true`` or ``DO_NOT_TRACK=1``. At most one ping
every 30 seconds per instance; the payload is the service name, event, version and a random
install identifier.
"""
from __future__ import annotations

import os
import threading
import time
import uuid

DEFAULT_TELEMETRY_URL = "https://gateway.ysiddo-ai-projects.app/telemetry"
_started = False


def _logs_dir() -> str:
    try:
        from agentkit_mcp.core.config import settings

        return str(settings.LOGS_DIR)
    except Exception:
        return os.path.join(os.path.expanduser("~"), ".agentkit")


def _instance_id() -> str:
    """Random install identifier, persisted so repeated starts report the same value."""
    d = _logs_dir()
    path = os.path.join(d, ".telemetry_instance_id")
    try:
        os.makedirs(d, exist_ok=True)
        if os.path.exists(path):
            existing = open(path).read().strip()
            if existing:
                return existing
    except Exception:
        pass
    new_id = uuid.uuid4().hex[:16]
    try:
        with open(path, "w") as f:
            f.write(new_id)
    except Exception:
        pass
    return new_id



def _pyproject_version(pkg_name):
    import re
    here = os.path.dirname(os.path.abspath(__file__))
    for _ in range(5):
        cand = os.path.join(here, "pyproject.toml")
        if os.path.exists(cand):
            m = re.search(r'(?m)^version\s*=\s*"([^"]+)"', open(cand).read())
            if m:
                return m.group(1)
        here = os.path.dirname(here)
    return "unknown"


def agentkit_version() -> str:
    try:
        from importlib.metadata import version

        return version("agentkit-mcp")
    except Exception:
        return _pyproject_version("agentkit-mcp")


def _opted_out() -> bool:
    flag = os.environ.get("TELEMETRY_OPT_OUT", "").strip().lower()
    return flag in ("1", "true", "yes") or os.environ.get("DO_NOT_TRACK", "").strip() == "1"


def _send() -> None:
    if _opted_out():
        return
    url = (os.environ.get("TELEMETRY_URL") or DEFAULT_TELEMETRY_URL).strip()
    if not url:
        return
    lock = os.path.join(_logs_dir(), ".telemetry_last_ping")
    try:
        if os.path.exists(lock) and time.time() - os.path.getmtime(lock) < 30:
            return
        with open(lock, "w") as f:
            f.write(str(time.time()))
    except Exception:
        pass
    payload = {
        "service": "AgentKit",
        "event": "startup",
        "version": agentkit_version(),
        "instance_id": _instance_id(),
    }
    import httpx

    for attempt in range(3):
        try:
            httpx.post(url, json=payload, timeout=3)
            return
        except Exception:
            time.sleep(2 * (attempt + 1))


def send_startup_ping() -> None:
    """Fire the ping once per process, in the background, without ever raising."""
    global _started
    if _started or os.environ.get("PYTEST_CURRENT_TEST"):
        return
    _started = True
    threading.Thread(target=_send, daemon=True).start()
