"""LIVE 3-agent workflow test — real LLM (needs key + langgraph). Proves the planner→analyst→
reporter graph runs end-to-end on real DataFrame data and produces a substantive report.
"""

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

pytestmark = pytest.mark.skipif(
    not (os.getenv("ANTHROPIC_API_KEY") or os.getenv("GROQ_API_KEY")),
    reason="live test needs an LLM key",
)


def test_workflow_analyze_produces_real_report():
    pytest.importorskip("langgraph")
    from agentkit_mcp.workflow import analyze

    out = analyze("What is our company's overall financial health right now?")
    print("\nLIVE workflow report (first 200 chars):", str(out.get("report"))[:200])
    assert "error" not in out, out
    report = out.get("report") or ""
    assert "stub" not in report.lower() and len(report) > 120  # substantive, non-stub
