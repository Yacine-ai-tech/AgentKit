"""
Structured logging for the entire platform.

Usage::

    from agentkit_mcp.core.logger import get_logger
    log = get_logger(__name__)
    log.info("Server started on port %d", port)
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from agentkit_mcp.core.config import settings

_LOG_DIR = Path(settings.LOGS_DIR)
_LOG_DIR.mkdir(parents=True, exist_ok=True)
_LOG_FILE = _LOG_DIR / "app.log"

_configured = False


def _configure_once() -> None:
    global _configured
    if _configured:
        return
    _configured = True

    root = logging.getLogger()
    root.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

    fmt = logging.Formatter(settings.LOG_FORMAT)

    # Console handler — stderr, not stdout. In MCP_TRANSPORT=stdio mode, stdout IS the
    # JSON-RPC wire; any plain-text log line written there would corrupt the protocol
    # stream from the client's point of view. Docker/Render capture stderr in their log
    # aggregation the same as stdout, so this doesn't lose anything in SSE/HTTP mode.
    sh = logging.StreamHandler(sys.stderr)
    sh.setFormatter(fmt)
    root.addHandler(sh)

    # File handler
    fh = logging.FileHandler(_LOG_FILE, encoding="utf-8")
    fh.setFormatter(fmt)
    root.addHandler(fh)

    # Suppress noisy third-party loggers
    for noisy in ("httpx", "httpcore", "chromadb", "sentence_transformers", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger; auto-configures on first call."""
    _configure_once()
    return logging.getLogger(name)
