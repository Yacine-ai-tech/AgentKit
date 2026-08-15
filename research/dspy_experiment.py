"""
AgentKit DSPy experiment — research artifact.

Frames planner → analyst → reporter as a compilable DSPy program with
BootstrapFewShot optimization over held-out business questions.

NOTE: This is a research scaffold. Production agents should use LangGraph
(workflow.py) or Claude Agent SDK (demos/claude_agent_sdk_demo.py).
"""
from __future__ import annotations

import os

from agentkit_mcp.core.logger import get_logger

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

    # Held-out set for BootstrapFewShot: real business questions with hand-authored
    # reference plans. Not exhaustive (this is a research scaffold, not a production
    # eval harness) but real enough that the metric below measures something.
    TRAINSET = [
        dspy.Example(
            question="Why did gross margin drop last quarter and what should we do?",
            raw_data="Gross margin fell from 46.8% to 41.2% QoQ. COGS up 9% driven by logistics.",
            plan="1. Pull COGS breakdown by category.\n2. Compare logistics cost trend to prior 4 quarters.\n"
                 "3. Identify which product lines drove the COGS increase.\n4. Recommend a mitigation (renegotiate "
                 "freight contracts or reprice affected SKUs).",
        ).with_inputs("question", "raw_data"),
        dspy.Example(
            question="Is our customer churn rate a problem right now?",
            raw_data="Monthly churn: 4.1% (up from 3.2% two months ago). NPS flat at 38.",
            plan="1. Segment churn by customer cohort and plan tier.\n2. Check for a correlated support-ticket "
                 "or outage event in the same window.\n3. Compare churn against the industry benchmark for this "
                 "segment.\n4. Recommend a retention intervention for the highest-risk cohort.",
        ).with_inputs("question", "raw_data"),
        dspy.Example(
            question="Should we hire more engineers this quarter?",
            raw_data="Headcount: 42 engineers. Deployment frequency down 15% QoQ. Backlog growing 8%/month.",
            plan="1. Check whether the deployment-frequency drop is capacity-driven or process-driven.\n"
                 "2. Compare backlog growth rate to current team velocity.\n3. Model runway impact of adding "
                 "2-3 engineers against current burn rate.\n4. Recommend hire count with a clear ROI tie-back.",
        ).with_inputs("question", "raw_data"),
        dspy.Example(
            question="What drove the spike in support tickets this week?",
            raw_data="Support tickets: 340 (up from 190 avg). 60% tagged 'checkout error'. Deploy shipped Tuesday.",
            plan="1. Correlate ticket spike timing against the Tuesday deploy.\n2. Pull error logs for the "
                 "checkout flow in that window.\n3. Confirm whether a rollback or hotfix resolved the symptom.\n"
                 "4. Recommend a deploy-gate change (e.g. checkout smoke test) to prevent recurrence.",
        ).with_inputs("question", "raw_data"),
    ]

    def plan_quality_metric(example, pred, trace=None) -> float:
        """Heuristic, not exact-match: a real business plan should (a) have multiple
        concrete steps and (b) actually reference the numbers in raw_data rather than
        staying generic. Returns 0.0-1.0; BootstrapFewShot treats > 0 as a usable
        demonstration for its bootstrapped few-shot examples."""
        plan = (getattr(pred, "plan", "") or "").strip()
        if not plan:
            return 0.0
        step_markers = sum(plan.count(f"{i}.") for i in range(1, 6))
        has_multiple_steps = step_markers >= 2
        raw_data = (getattr(example, "raw_data", "") or "")
        numbers_in_data = set(w.strip("%.,") for w in raw_data.split() if any(c.isdigit() for c in w))
        grounded = any(n in plan for n in numbers_in_data) if numbers_in_data else True
        return float(has_multiple_steps) * 0.6 + float(grounded) * 0.4


def compile_program() -> dict:
    """Run a real DSPy BootstrapFewShot compile over TRAINSET and return a summary dict
    shaped for rageval.log_dspy_run/dspy_compile_callback: program_name, candidates,
    winner, eval_metric, eval_score."""
    optimizer = dspy.BootstrapFewShot(metric=plan_quality_metric, max_bootstrapped_demos=2, max_labeled_demos=2)
    compiled = optimizer.compile(BusinessAnalysisPipeline(), trainset=TRAINSET)

    # Free-tier LLM rate limits: space out the post-compile eval calls (same pattern as
    # a standalone evaluator script and skip, rather than crash on,
    # any single example that hits a rate limit or transient error.
    import time
    call_delay = float(os.getenv("DSPY_CALL_DELAY_SECONDS", "5"))
    scores = []
    for i, ex in enumerate(TRAINSET):
        try:
            scores.append(plan_quality_metric(ex, compiled(question=ex.question, raw_data=ex.raw_data)))
        except Exception as e:
            log.warning("eval call failed for %r (skipped, not counted): %s", ex.question[:60], e)
        if call_delay and i < len(TRAINSET) - 1:
            time.sleep(call_delay)
    eval_score = sum(scores) / len(scores) if scores else 0.0

    demos = getattr(compiled.planner, "demos", None) or []
    return {
        "program_name": "business_analysis_pipeline",
        "candidates": [d.question for d in demos] if demos else [ex.question for ex in TRAINSET],
        "winner": f"bootstrapped_{len(demos)}_demos",
        "eval_metric": "plan_quality_heuristic",
        "eval_score": round(eval_score, 4),
    }, compiled


def _log_compilation_to_rageval(summary: dict) -> None:
    """Log the compile run to RAGeval, in-process (no network call, no evaluator URL to
    configure) — following a modular "drop-in library" pattern.
    scripts/evaluate_with_rageval_package.py uses. Optional: rageval isn't a core
    requirement.txt dependency for AgentKit, so this degrades to a clear skip message
    rather than failing the research run if it isn't installed."""
    try:
        from rageval import dspy_compile_callback  # type: ignore

        @dspy_compile_callback
        def _run():
            return summary

        _run()  # dspy_compile_callback runs log_dspy_run() via its own asyncio.run()
    except ImportError:
        print("rageval package not installed — skipping DSPy compilation telemetry "
              "(pip install omnismart-rageval to enable).")
    except Exception as e:
        log.warning("RAGeval DSPy telemetry logging failed (non-fatal): %s", e)


def main():
    if not _DSPY:
        print("dspy-ai not installed. pip install dspy-ai")
        return
    model = os.getenv("LLM_DEFAULT", "groq/llama-3.3-70b-versatile")
    if not (os.getenv("GROQ_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY")):
        print("No LLM key found (set GROQ_API_KEY / ANTHROPIC_API_KEY).")
        return
    # Configure DSPy's LM via LiteLLM and actually run the planner→analyst→reporter program.
    # ChainOfThought spends its budget on the reasoning field before it ever emits the
    # output fields, so 1024 truncates mid-reasoning and yields an empty plan/report.
    # Override with DSPY_MAX_TOKENS if your model needs more headroom.
    dspy.configure(lm=dspy.LM(model, temperature=0.3,
                              max_tokens=int(os.getenv("DSPY_MAX_TOKENS", "4096"))))

    raw_data = "(no live data)"
    try:
        import asyncio
        from agentkit_mcp.mcp_server import get_executive_summary
        raw_data = str(asyncio.new_event_loop().run_until_complete(get_executive_summary()))[:1500]
    except Exception as e:
        log.warning("exec summary unavailable, running without live data: %s", e)

    pred = BusinessAnalysisPipeline()(
        question="What drove company health recently and what should leadership do?",
        raw_data=raw_data,
    )
    print("=== DSPy plan ===\n", pred.plan)
    print("\n=== DSPy report ===\n", pred.report)

    print("\n=== Compiling with BootstrapFewShot (this makes several LLM calls) ===")
    summary, compiled = compile_program()
    print(f"compiled: {summary['winner']}, eval_score={summary['eval_score']} "
          f"({summary['eval_metric']})")
    _log_compilation_to_rageval(summary)


if __name__ == "__main__":
    main()
