"""
AgentKit DSPy experiment — research artifact.

Frames planner → analyst → reporter as a compilable DSPy program with
BootstrapFewShot optimization over held-out business questions.

NOTE: This is a research scaffold. Production agents should use LangGraph
(workflow.py) or Claude Agent SDK (demos/claude_agent_sdk_demo.py).
"""
from __future__ import annotations

import os

from core.logger import get_logger

log = get_logger(__name__)

try:
    import dspy  # type: ignore
    _DSPY = True
except ImportError:
    _DSPY = False
    log.warning("dspy-ai not installed — experiment unavailable")


if _DSPY:
    class Planner(dspy.Signature):
        """Produce a 3-4 step plan for a business analysis question."""
        question = dspy.InputField()
        plan = dspy.OutputField()

    class Analyst(dspy.Signature):
        """Decide which KPI tools to call given a plan."""
        plan = dspy.InputField()
        tool_calls = dspy.OutputField(desc="JSON list of tool_name, args")

    class Reporter(dspy.Signature):
        """Synthesize an executive report from raw data and a plan."""
        plan = dspy.InputField()
        raw_data = dspy.InputField()
        report = dspy.OutputField()

    class BusinessAnalysisPipeline(dspy.Module):
        def __init__(self):
            super().__init__()
            self.planner = dspy.ChainOfThought(Planner)
            self.analyst = dspy.ChainOfThought(Analyst)
            self.reporter = dspy.ChainOfThought(Reporter)

        def forward(self, question: str, raw_data: str = ""):
            plan = self.planner(question=question).plan
            tools = self.analyst(plan=plan).tool_calls
            report = self.reporter(plan=plan, raw_data=raw_data).report
            return dspy.Prediction(plan=plan, tools=tools, report=report)


def main():
    if not _DSPY:
        print("dspy-ai not installed. pip install dspy-ai")
        return
    model = os.getenv("LLM_DEFAULT", "groq/llama-3.3-70b-versatile")
    if not (os.getenv("GROQ_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY")):
        print("No LLM key found (set GROQ_API_KEY / ANTHROPIC_API_KEY).")
        return
    # Configure DSPy's LM via LiteLLM and actually run the planner→analyst→reporter program.
    dspy.configure(lm=dspy.LM(model, temperature=0.3, max_tokens=1024))

    raw_data = "(no live data)"
    try:
        import asyncio
        from mcp_server import get_executive_summary
        raw_data = str(asyncio.new_event_loop().run_until_complete(get_executive_summary()))[:1500]
    except Exception as e:
        log.warning("exec summary unavailable, running without live data: %s", e)

    pred = BusinessAnalysisPipeline()(
        question="What drove company health recently and what should leadership do?",
        raw_data=raw_data,
    )
    print("=== DSPy plan ===\n", pred.plan)
    print("\n=== DSPy report ===\n", pred.report)


if __name__ == "__main__":
    main()
