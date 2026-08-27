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

    # Compact (question, raw_data, plan) rows shared by TRAINSET (fed to BootstrapFewShot as
    # candidate demonstrations) and EVALSET (held out — never shown to the optimizer, used only
    # to score compile_program()'s output). Real, hand-authored business questions across a
    # range of domains, each with a plan that references the concrete numbers in raw_data.
    _ROWS = [
        ("Why did gross margin drop last quarter and what should we do?",
         "Gross margin fell from 46.8% to 41.2% QoQ. COGS up 9% driven by logistics.",
         "1. Pull COGS breakdown by category.\n2. Compare logistics cost trend to prior 4 quarters.\n"
         "3. Identify which product lines drove the COGS increase.\n4. Recommend a mitigation "
         "(renegotiate freight contracts or reprice affected SKUs)."),
        ("Is our customer churn rate a problem right now?",
         "Monthly churn: 4.1% (up from 3.2% two months ago). NPS flat at 38.",
         "1. Segment churn by customer cohort and plan tier.\n2. Check for a correlated support-ticket "
         "or outage event in the same window.\n3. Compare churn against the industry benchmark for this "
         "segment.\n4. Recommend a retention intervention for the highest-risk cohort."),
        ("Should we hire more engineers this quarter?",
         "Headcount: 42 engineers. Deployment frequency down 15% QoQ. Backlog growing 8%/month.",
         "1. Check whether the deployment-frequency drop is capacity-driven or process-driven.\n"
         "2. Compare backlog growth rate to current team velocity.\n3. Model runway impact of adding "
         "2-3 engineers against current burn rate.\n4. Recommend hire count with a clear ROI tie-back."),
        ("What drove the spike in support tickets this week?",
         "Support tickets: 340 (up from 190 avg). 60% tagged 'checkout error'. Deploy shipped Tuesday.",
         "1. Correlate ticket spike timing against the Tuesday deploy.\n2. Pull error logs for the "
         "checkout flow in that window.\n3. Confirm whether a rollback or hotfix resolved the symptom.\n"
         "4. Recommend a deploy-gate change (e.g. checkout smoke test) to prevent recurrence."),
        ("Why did marketing CAC jump this month?",
         "CAC rose from $84 to $131 (+56%). Paid social spend up 40%, conversion rate down from 3.1% to 2.0%.",
         "1. Break CAC change into spend-driven vs conversion-driven components.\n2. Check whether the "
         "conversion drop is channel-specific or landing-page-wide.\n3. Compare cohort quality (LTV) for "
         "leads acquired at the higher CAC.\n4. Recommend pausing or reallocating the weakest channel."),
        ("Are we at risk of missing this quarter's revenue target?",
         "Pipeline coverage: 2.1x target (down from 3.4x last quarter). Win rate steady at 22%. 6 weeks left.",
         "1. Compare current pipeline coverage against the historical coverage-to-close-rate needed to "
         "hit target.\n2. Identify which stage of the funnel lost the most coverage.\n3. Check whether "
         "win rate is holding steady across all reps or masking a decline in a subset.\n4. Recommend a "
         "pipeline-generation push or a target reforecast, whichever the math supports."),
        ("Is our infrastructure spend under control?",
         "Cloud spend: $184k/mo (up from $146k, +26% QoQ). Traffic grew 11% in the same window.",
         "1. Compare the 26% cost growth against the 11% traffic growth to size the efficiency gap.\n"
         "2. Break the increase down by service (compute, storage, egress).\n3. Check for idle or "
         "overprovisioned resources contributing disproportionately.\n4. Recommend a rightsizing pass "
         "or reserved-capacity commitment for the largest driver."),
        ("Should we be worried about the drop in NPS?",
         "NPS fell from 52 to 38 over two quarters. Detractor comments cluster around onboarding friction.",
         "1. Segment the NPS drop by customer tenure to see if it's concentrated in new users.\n"
         "2. Pull the top detractor themes and quantify how many responses cite onboarding.\n"
         "3. Compare time-to-first-value before and after the onboarding flow changed.\n"
         "4. Recommend a specific onboarding fix tied to the most-cited friction point."),
        ("What's driving the increase in employee attrition?",
         "Voluntary attrition: 18% annualized (up from 11%). Concentrated in engineering, tenure 1-2 years.",
         "1. Confirm the attrition concentration by team and tenure band with exit-survey data.\n"
         "2. Compare comp bands for the affected cohort against current market rates.\n"
         "3. Check whether attrition correlates with a specific manager, team, or project.\n"
         "4. Recommend a targeted retention action (comp adjustment or manager intervention) for the "
         "highest-risk cohort."),
        ("Is the new pricing tier cannibalizing our mid-tier plan?",
         "Mid-tier signups down 22% since the new tier launched 6 weeks ago; new-tier signups up 340 accounts.",
         "1. Check what fraction of new-tier signups are net-new vs. downgrades from mid-tier.\n"
         "2. Compare blended ARPU before and after the new tier launched.\n3. Segment cannibalization by "
         "customer size to see if it's concentrated in one segment.\n4. Recommend a packaging adjustment "
         "if net revenue per account is falling."),
        ("Why is our on-time delivery rate slipping?",
         "On-time delivery: 87% (down from 96%). Third-party carrier delays account for most late shipments.",
         "1. Break the delay rate down by carrier to isolate the underperforming one(s).\n2. Compare "
         "delay rates by region to check for a route-specific bottleneck.\n3. Check whether order volume "
         "growth outpaced carrier capacity in the same window.\n4. Recommend a carrier renegotiation or "
         "diversification for the worst-performing lane."),
        ("Should we be concerned about the rise in failed login attempts?",
         "Failed logins: 12,400/day (up from 1,800/day baseline). Concentrated on the password-reset endpoint.",
         "1. Determine whether the spike matches a known credential-stuffing pattern (IP/user-agent "
         "diversity, request rate).\n2. Check current rate-limiting and lockout thresholds on the "
         "affected endpoint.\n3. Cross-reference a sample of targeted accounts against known breach "
         "lists.\n4. Recommend an immediate mitigation (rate limiting, CAPTCHA, forced reset) scoped to "
         "the affected endpoint."),
        ("Is our sales cycle getting longer, and does it matter?",
         "Average sales cycle: 74 days (up from 58 days). Deal size and win rate both roughly flat.",
         "1. Break the cycle-length increase down by deal stage to find where time is being added.\n"
         "2. Check whether the increase concentrates in a specific segment (e.g. enterprise vs SMB).\n"
         "3. Compare against a benchmark for deals of this size to judge whether 74 days is actually "
         "a problem or in line with market.\n4. Recommend a process fix for the stage adding the most "
         "time, only if it's shown to correlate with lower win rate."),
        ("What's behind the drop in warehouse pick accuracy?",
         "Pick accuracy: 96.1% (down from 99.2%). Error rate highest on the newest SKU set.",
         "1. Confirm whether errors concentrate on the newly introduced SKUs or are spread evenly.\n"
         "2. Check whether those SKUs share a bin-location or labeling issue.\n3. Compare error rates "
         "between staff trained before vs after the new SKU rollout.\n4. Recommend a targeted fix "
         "(relabeling, bin reassignment, or retraining) scoped to the affected SKU set."),
        ("Is our app's crash rate acceptable for this release?",
         "Crash-free session rate: 98.7% (target 99.5%). 70% of crashes concentrated on one Android device class.",
         "1. Confirm the device-class concentration against the full crash log, not just a sample.\n"
         "2. Check whether the crashing code path is device-specific (memory-constrained hardware) or "
         "a general bug that device class just surfaces first.\n3. Compare crash-free rate on that "
         "device class before this release to isolate what changed.\n4. Recommend a hotfix or "
         "device-specific mitigation before wider rollout."),
        ("Why did our support first-response time regress?",
         "First-response time: 6.2 hours (up from 2.1 hours). Ticket volume up 18%, headcount unchanged.",
         "1. Confirm whether the regression tracks proportionally with the volume increase or exceeds it.\n"
         "2. Break response time down by ticket priority to see if urgent tickets are also affected.\n"
         "3. Check current queue-routing rules for a bottleneck (e.g. one queue absorbing "
         "disproportionate volume).\n4. Recommend a staffing or routing fix sized to the actual gap, "
         "not just the headline number."),
        ("Should we renegotiate our largest vendor contract?",
         "Vendor spend: $2.1M/yr, 34% of total vendor spend. Contract renews in 90 days; market rate is ~15% lower.",
         "1. Confirm the 15% market-rate gap against at least one comparable quote, not a single "
         "benchmark source.\n2. Check contract terms for early-termination or renegotiation clauses "
         "ahead of the 90-day renewal.\n3. Weigh switching cost and migration risk against the "
         "savings.\n4. Recommend opening renegotiation now, using the 90-day window and comparable "
         "quotes as leverage."),
        ("Is our email deliverability problem hurting revenue?",
         "Inbox placement rate: 71% (down from 94%). Email drives an estimated 18% of monthly revenue.",
         "1. Confirm the deliverability drop against sender-reputation and blocklist status, not just "
         "placement-rate tooling.\n2. Identify the specific trigger (recent list-hygiene change, "
         "content flagged as spam, authentication misconfiguration).\n3. Estimate revenue at risk from "
         "the placement-rate drop using the 18% revenue-attribution figure.\n4. Recommend the specific "
         "remediation (re-authentication, list cleanup, sending-domain warmup) for the root cause found."),
        ("Why is our free-to-paid conversion rate falling?",
         "Free-to-paid conversion: 4.8% (down from 7.2%). Signups up 30%, driven by a new low-intent channel.",
         "1. Check whether the conversion drop is a genuine rate decline or a mix-shift from the new "
         "channel bringing in lower-intent users.\n2. Compare conversion rate for the new channel's "
         "cohort against the prior baseline cohorts.\n3. If it's mix-shift, recompute the like-for-like "
         "conversion rate on the original channels alone.\n4. Recommend either a channel-quality fix or "
         "confirm no action is needed if the underlying funnel is healthy."),
        ("Should we be worried about customer concentration risk?",
         "Top 5 customers: 47% of ARR (up from 31% two years ago). Largest single customer: 19% of ARR.",
         "1. Confirm the concentration trend isn't just an artifact of overall ARR growth diluting the "
         "denominator differently.\n2. Check contract terms and renewal dates for the top 5, especially "
         "the 19%-ARR customer.\n3. Assess churn-risk signals (usage trend, support tickets, exec "
         "sponsor changes) for that customer specifically.\n4. Recommend a diversification push or an "
         "account-specific retention plan depending on what the risk assessment shows."),
        ("Is our API's p99 latency regression a real problem?",
         "p99 latency: 1,840ms (up from 620ms) on the search endpoint. Traffic and error rate both flat.",
         "1. Confirm the regression is genuinely at p99 and not an artifact of a monitoring change.\n"
         "2. Check for a correlated deploy, index change, or dependency-version bump in the same "
         "window.\n3. Profile whether the tail latency is concentrated on a specific query shape or "
         "spread evenly.\n4. Recommend a rollback or targeted fix for the identified cause before it "
         "affects a wider percentile."),
        ("Why did our manufacturing defect rate spike?",
         "Defect rate: 3.4% (up from 0.8%). Coincides with a new raw-material supplier switch two weeks ago.",
         "1. Confirm the timing correlation between the supplier switch and the defect-rate spike "
         "against the production log, not just calendar proximity.\n2. Pull incoming-material QC data "
         "for the new supplier's batches.\n3. Compare defect rate on units made with old vs new "
         "material stock, if both are still in the line.\n4. Recommend reverting to the prior supplier "
         "or quarantining the new material pending root-cause confirmation."),
        ("Should we expand into the new geographic market we're piloting?",
         "Pilot market: 3 months in, CAC 1.4x higher than home market, but retention tracking 10% ahead.",
         "1. Confirm both the CAC and retention figures are measured on comparable cohorts and time "
         "windows.\n2. Project LTV:CAC for the pilot market using its own retention curve, not the home "
         "market's.\n3. Identify what's driving the higher CAC (channel cost, brand awareness, "
         "competition) to judge if it's structural or a launch-phase cost.\n4. Recommend continuing, "
         "scaling, or pausing the pilot based on the LTV:CAC comparison, not CAC alone."),
        ("Is our data pipeline's growing failure rate a capacity problem?",
         "Pipeline job failure rate: 6.2% (up from 0.9%). Data volume grew 3x in the same period.",
         "1. Check whether failures correlate with job size/volume or are spread evenly regardless of "
         "load.\n2. Pull error types for the failing jobs (timeout, OOM, schema mismatch) to separate "
         "capacity issues from data-quality issues.\n3. Compare current resource allocation against the "
         "3x volume growth to quantify the capacity gap.\n4. Recommend a scaling change if capacity-"
         "bound, or a schema/data-quality fix if not."),
        ("Why did our ad-supported product's revenue per user drop?",
         "ARPU: $0.42/mo (down from $0.61/mo). Impressions per session down 15%, fill rate flat.",
         "1. Confirm the ARPU drop traces to impressions-per-session rather than eCPM or fill rate.\n"
         "2. Check whether a recent UI change reduced ad slot visibility or session length.\n"
         "3. Compare the impressions-per-session trend across platforms (web vs mobile) to localize the "
         "cause.\n4. Recommend reverting or adjusting the UI change if it's the confirmed driver."),
        ("Should we be concerned about the increase in refund requests?",
         "Refund rate: 5.1% (up from 1.9%). 65% of refunds cite 'not as described' on one product category.",
         "1. Confirm the concentration in one product category against the full refund-reason "
         "breakdown, not a sample.\n2. Compare that category's product listing/marketing copy against "
         "actual product specs for a mismatch.\n3. Check whether the spike started at a specific "
         "listing-copy or packaging change.\n4. Recommend correcting the listing or packaging for the "
         "flagged category before the refund rate compounds into review damage."),
        ("Is our contact center's average handle time increase a training issue?",
         "Average handle time: 11.4 min (up from 7.8 min). New hires make up 40% of current agent pool.",
         "1. Compare handle time for new hires vs. tenured agents to isolate whether it's a tenure "
         "effect.\n2. Check if a recent policy or tooling change added steps to every call regardless "
         "of agent tenure.\n3. Weight the two effects (tenure mix vs. process change) by their relative "
         "contribution to the overall increase.\n4. Recommend targeted new-hire coaching if tenure-"
         "driven, or a process simplification if it's a policy/tooling effect."),
        ("Why is our subscription upgrade rate stalling?",
         "Tier-upgrade rate: 2.3% (flat for 3 months after averaging 4.1% the prior year).",
         "1. Check whether usage against tier limits (the typical upgrade trigger) has also gone flat.\n"
         "2. Compare in-app upgrade prompts' click-through rate now vs. a year ago for a UX regression.\n"
         "3. Check for a pricing or packaging change that made the next tier a worse deal.\n"
         "4. Recommend a specific fix (usage-based nudges, pricing adjustment) tied to whichever cause "
         "the data supports."),
        ("Should we worry about the rise in code-review turnaround time?",
         "Median PR review time: 18 hours (up from 6 hours). PR count per engineer roughly flat.",
         "1. Confirm the increase isn't explained by larger PR size (lines changed) rather than review "
         "process.\n2. Check reviewer-load distribution — whether review requests are concentrated on a "
         "small number of engineers.\n3. Compare turnaround time across teams to see if it's org-wide "
         "or localized.\n4. Recommend a reviewer-load rebalancing or PR-size guideline depending on "
         "which factor the data points to."),
        ("Is the increase in cart abandonment rate linked to the new checkout flow?",
         "Cart abandonment: 74% (up from 61%). New checkout flow shipped 2 weeks ago, adds one extra step.",
         "1. Compare abandonment rate before and after the exact ship date of the new flow.\n"
         "2. Break abandonment down by the specific step where users drop off in the new flow.\n"
         "3. Check whether abandonment rose on both desktop and mobile or just one.\n4. Recommend "
         "reverting the extra step or A/B testing a simplified version against the abandonment "
         "baseline."),
        ("Why did our field sales team's quota attainment drop this quarter?",
         "Quota attainment: 58% of reps at or above quota (down from 79%). New comp plan rolled out this quarter.",
         "1. Compare attainment for reps under the new comp plan vs. any still grandfathered on the "
         "old one.\n2. Check whether pipeline generation (not just close rate) also declined under the "
         "new plan.\n3. Survey whether the new plan changed incentives in a way that shifted rep "
         "behavior (e.g. toward smaller, faster deals).\n4. Recommend a comp-plan adjustment if it's "
         "the confirmed driver, backed by the grandfathered-rep comparison."),
        ("Should we consolidate our two overlapping analytics tools?",
         "Tool A: $86k/yr, 40% weekly active use. Tool B: $102k/yr, 65% weekly active use. Feature overlap ~70%.",
         "1. Confirm the 70% feature-overlap estimate against an actual audit of dashboards built in "
         "each tool.\n2. Compare migration cost/effort for consolidating onto Tool B against the "
         "combined $188k/yr spend.\n3. Identify any Tool A-only workflows that would need a replacement "
         "before cutover.\n4. Recommend consolidating onto the higher-adoption tool once the migration "
         "gap is closed."),
        ("Why did our mobile app's install-to-signup rate drop?",
         "Install-to-signup: 34% (down from 52%). New onboarding screen added before signup two weeks ago.",
         "1. Compare the drop-off point in the funnel before and after the new screen was added.\n"
         "2. Check whether the drop is uniform across platforms (iOS vs Android) or one-sided.\n"
         "3. Pull session-replay or analytics on the new screen for an unusually high exit rate.\n"
         "4. Recommend simplifying or removing the new screen if it's the confirmed drop-off point."),
        ("Is our warehouse overtime spend justified?",
         "Overtime spend: $58k/mo (up from $19k/mo). Order volume up 22%, headcount unchanged.",
         "1. Compare the overtime-cost increase against the 22% volume growth to see if it's "
         "proportionate.\n2. Check whether overtime concentrates on specific shifts or is spread "
         "evenly, which would point to a scheduling fix vs. a genuine capacity shortfall.\n"
         "3. Model the cost of hiring additional headcount against sustained overtime pay at this "
         "volume.\n4. Recommend a hiring plan if volume growth looks durable, or a scheduling fix if "
         "overtime is concentrated and avoidable."),
        ("Should we be worried about declining engagement on our community forum?",
         "Daily active posters: 1,240 (down from 2,100). Total registered users still growing 5%/mo.",
         "1. Confirm the engagement drop is a genuine behavior change, not a measurement artifact from "
         "a recent tracking change.\n2. Check whether the drop concentrates among long-tenured users "
         "(possible fatigue) or new users (possible onboarding gap).\n3. Compare against any recent "
         "moderation-policy or UI change to the forum.\n4. Recommend a specific re-engagement or "
         "onboarding fix tied to whichever cohort the data implicates."),
        ("Why is our procurement cycle time increasing?",
         "Average PO approval time: 9.4 days (up from 3.1 days). Approval-chain length unchanged.",
         "1. Confirm the increase isn't explained by a change in average PO dollar value crossing "
         "approval thresholds.\n2. Check where in the approval chain requests are stalling longest.\n"
         "3. Compare cycle time across departments to see if it's org-wide or localized to one team.\n"
         "4. Recommend a specific process fix (delegation, threshold adjustment) for the stage found "
         "to be the bottleneck."),
        ("Is our influencer marketing spend generating a positive return?",
         "Influencer spend: $210k this quarter. Attributed revenue: $340k (1.62x ROAS), down from 2.4x last quarter.",
         "1. Confirm the attribution methodology hasn't changed between quarters before comparing "
         "ROAS directly.\n2. Break ROAS down by influencer tier/cohort to find whether the decline is "
         "broad or concentrated in a few underperforming partnerships.\n3. Compare cost-per-influencer "
         "this quarter against last quarter for a pricing-driven explanation.\n4. Recommend reallocating "
         "spend away from the underperforming cohort, or renegotiating rates, based on what the "
         "breakdown shows."),
        ("Should we be concerned about the rise in security-patch lag time?",
         "Median time-to-patch for critical CVEs: 21 days (up from 6 days). Patch backlog: 34 open items.",
         "1. Confirm the lag increase against the patch-tracking system, not anecdotal reports.\n"
         "2. Check whether the backlog growth is a capacity issue (patching team size) or a process "
         "issue (change-approval bottleneck).\n3. Prioritize the 34 open items by severity and exposure "
         "to identify the ones carrying the most immediate risk.\n4. Recommend a specific remediation "
         "(temporary capacity increase, expedited approval path for critical CVEs) sized to close the "
         "gap on the highest-risk items first."),
    ]

    TRAINSET = [
        dspy.Example(question=q, raw_data=d, plan=p).with_inputs("question", "raw_data")
        for q, d, p in _ROWS[:8]
    ]
    # Held out from BootstrapFewShot entirely — used only to score compile_program()'s
    # output, so the reported eval_score reflects generalization, not memorized demos.
    EVALSET = [
        dspy.Example(question=q, raw_data=d, plan=p).with_inputs("question", "raw_data")
        for q, d, p in _ROWS[8:]
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
        raw_data = getattr(example, "raw_data", "") or ""
        numbers_in_data = set(
            w.strip("%.,") for w in raw_data.split() if any(c.isdigit() for c in w)
        )
        grounded = any(n in plan for n in numbers_in_data) if numbers_in_data else True
        return float(has_multiple_steps) * 0.6 + float(grounded) * 0.4


def _eval_on(program, examples: list, call_delay: float) -> tuple:
    """Score `program` against a held-out set, spacing calls out for free-tier LLM rate
    limits and skipping (not crashing on) any single example that hits a transient error.
    Returns (mean_score, n_scored)."""
    import time

    scores = []
    for i, ex in enumerate(examples):
        try:
            scores.append(
                plan_quality_metric(ex, program(question=ex.question, raw_data=ex.raw_data))
            )
        except Exception as e:
            log.warning(
                "eval call failed for %r (skipped, not counted): %s", ex.question[:60], e
            )
        if call_delay and i < len(examples) - 1:
            time.sleep(call_delay)
    return (sum(scores) / len(scores) if scores else 0.0), len(scores)


def compile_program() -> dict:
    """Run a real DSPy BootstrapFewShot compile over TRAINSET and return a summary dict
    shaped for rageval.log_dspy_run/dspy_compile_callback: program_name, candidates,
    winner, eval_metric, eval_score, plus an uncompiled-vs-compiled comparison. Both
    conditions are scored on EVALSET, which BootstrapFewShot never sees during compilation,
    so the comparison reflects generalization rather than memorized training demos."""
    call_delay = float(os.getenv("DSPY_CALL_DELAY_SECONDS", "5"))

    uncompiled_score, uncompiled_n = _eval_on(
        BusinessAnalysisPipeline(), EVALSET, call_delay
    )

    optimizer = dspy.BootstrapFewShot(
        metric=plan_quality_metric, max_bootstrapped_demos=2, max_labeled_demos=2
    )
    compiled = optimizer.compile(BusinessAnalysisPipeline(), trainset=TRAINSET)
    eval_score, scored_n = _eval_on(compiled, EVALSET, call_delay)

    demos = getattr(compiled.planner, "demos", None) or []
    return {
        "program_name": "business_analysis_pipeline",
        "candidates": (
            [d.question for d in demos] if demos else [ex.question for ex in TRAINSET]
        ),
        "winner": f"bootstrapped_{len(demos)}_demos",
        "eval_metric": "plan_quality_heuristic",
        "eval_score": round(eval_score, 4),
        "eval_n": scored_n,
        "uncompiled_eval_score": round(uncompiled_score, 4),
        "uncompiled_eval_n": uncompiled_n,
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
        print(
            "rageval package not installed — skipping DSPy compilation telemetry "
            "(pip install omnismart-rageval to enable)."
        )
    except Exception as e:
        log.warning("RAGeval DSPy telemetry logging failed (non-fatal): %s", e)


def main():
    if not _DSPY:
        print("dspy-ai not installed. pip install dspy-ai")
        return
    model = os.getenv("LLM_DEFAULT", "groq/openai/gpt-oss-120b")
    if not (
        os.getenv("GROQ_API_KEY")
        or os.getenv("ANTHROPIC_API_KEY")
        or os.getenv("OPENAI_API_KEY")
    ):
        print("No LLM key found (set GROQ_API_KEY / ANTHROPIC_API_KEY).")
        return
    # Configure DSPy's LM via LiteLLM and actually run the planner→analyst→reporter program.
    # ChainOfThought spends its budget on the reasoning field before it ever emits the
    # output fields, so 1024 truncates mid-reasoning and yields an empty plan/report.
    # Override with DSPY_MAX_TOKENS if your model needs more headroom.
    # num_retries is generous here (default is 3) because BootstrapFewShot's own compile
    # loop makes several chained LLM calls back-to-back with no delay between them —
    # on a free-tier per-minute token budget this reliably hits a transient 429 before
    # the window rolls over. litellm/DSPy back off and retry on 429 automatically; a
    # higher retry ceiling just gives that backoff enough attempts to ride out a ~10-20s
    # per-minute quota reset instead of surfacing it as a hard failure.
    dspy.configure(
        lm=dspy.LM(
            model, temperature=0.3, max_tokens=int(os.getenv("DSPY_MAX_TOKENS", "4096")),
            num_retries=int(os.getenv("DSPY_NUM_RETRIES", "8")),
        )
    )

    raw_data = "(no live data)"
    try:
        import asyncio

        from agentkit_mcp.mcp_server import get_executive_summary

        raw_data = str(
            asyncio.new_event_loop().run_until_complete(get_executive_summary())
        )[:1500]
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
    print(
        f"uncompiled: eval_score={summary['uncompiled_eval_score']} "
        f"(n={summary['uncompiled_eval_n']}, {summary['eval_metric']})"
    )
    print(
        f"compiled: {summary['winner']}, eval_score={summary['eval_score']} "
        f"(n={summary['eval_n']}, {summary['eval_metric']})"
    )
    _log_compilation_to_rageval(summary)


if __name__ == "__main__":
    main()
