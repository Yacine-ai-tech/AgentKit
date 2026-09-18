"""AgentKit multi-domain DSPy-style benchmark.

Evaluates the AgentKit LangGraph workflow across 15 scenarios spanning all
5 KPI domains: Finance, People, Operations, Customer, Engineering.

Resumption: results are appended atomically to a .jsonl cache file.
Any already-evaluated scenario ID is skipped on restart — zero duplicate
spend and zero repeated API calls.

Usage:
    python eval/run_dspy_eval.py
    python eval/run_dspy_eval.py --scenarios eval/multi_domain_scenarios.json
    python eval/run_dspy_eval.py --cache-file eval/cache/agentkit_eval_cache.jsonl
    python eval/run_dspy_eval.py --dry-run     # print scenarios, no API calls
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

EVAL_DIR = ROOT / "eval"
DEFAULT_SCENARIOS = EVAL_DIR / "multi_domain_scenarios.json"
DEFAULT_CACHE = EVAL_DIR / "cache" / "agentkit_eval_cache.jsonl"


# ---------------------------------------------------------------------------
# Cache helpers — append-only, $0 resumption
# ---------------------------------------------------------------------------

def _load_cache(cache_file: Path) -> set[str]:
    """Return the set of scenario IDs already evaluated."""
    done: set[str] = set()
    if not cache_file.exists():
        return done
    with cache_file.open() as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
                if "id" in d:
                    done.add(d["id"])
            except json.JSONDecodeError:
                pass
    return done


def _append_cache(cache_file: Path, record: dict) -> None:
    """Atomically append a single evaluated result to the cache."""
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    with cache_file.open("a") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Evaluation logic
# ---------------------------------------------------------------------------

def _score_result(scenario: dict, res: dict) -> dict:
    """Score a single workflow result against scenario expectations.

    Returns a scored record suitable for caching and reporting.
    """
    raw_data = res.get("raw_data", {}) or {}
    report = res.get("report", "") or ""
    invoked = list(raw_data.keys())

    expected_tools = scenario.get("expected_tools", [])
    expected_keywords = scenario.get("expected_keywords", [])
    min_len = scenario.get("min_report_length", 30)

    # Tool coverage: at least one expected tool was invoked
    tools_hit = [t for t in expected_tools if any(t in inv for inv in invoked)]
    tool_coverage = len(tools_hit) / max(len(expected_tools), 1)

    # Keyword coverage: fraction of expected keywords found in the report
    report_lower = report.lower()
    kw_hits = [kw for kw in expected_keywords if kw.lower() in report_lower]
    kw_coverage = len(kw_hits) / max(len(expected_keywords), 1)

    # Report quality: non-trivial length
    has_report = len(report.strip()) >= min_len

    # Overall pass: tool coverage >= 50% AND at least 1 keyword AND report ok
    passed = (tool_coverage >= 0.5) and (kw_coverage >= 0.25) and has_report

    return {
        "id": scenario["id"],
        "domain": scenario["domain"],
        "query": scenario["query"],
        "passed": passed,
        "tool_coverage": round(tool_coverage, 3),
        "kw_coverage": round(kw_coverage, 3),
        "has_report": has_report,
        "invoked_tools": invoked,
        "tools_hit": tools_hit,
        "report_length": len(report),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "error": None,
    }


def run_dspy_eval(
    scenarios_file: Path = DEFAULT_SCENARIOS,
    cache_file: Path = DEFAULT_CACHE,
    dry_run: bool = False,
) -> dict:
    """Run (or resume) the AgentKit multi-domain benchmark.

    Returns a summary dict with per-domain and overall scores.
    """
    if not scenarios_file.exists():
        print(f"[ERROR] Scenarios file not found: {scenarios_file}", file=sys.stderr)
        sys.exit(1)

    scenarios = json.loads(scenarios_file.read_text())
    done_ids = _load_cache(cache_file)

    print("AgentKit Multi-Domain DSPy Benchmark")
    print("=" * 60)
    print(f"Scenarios: {len(scenarios)} total | Already cached: {len(done_ids)}")
    print(f"Cache: {cache_file}")
    print()

    if dry_run:
        for s in scenarios:
            status = "SKIP (cached)" if s["id"] in done_ids else "RUN"
            print(f"  [{status}] {s['id']:12s} | {s['domain']:15s} | {s['query'][:60]}")
        print("\n[DRY RUN] No API calls made.")
        return {}

    # Lazy import — only needed when actually running
    try:
        from agentkit_mcp.workflow import analyze
    except ImportError as exc:
        print(f"[ERROR] Cannot import agentkit_mcp.workflow: {exc}", file=sys.stderr)
        print("  Ensure you run from the AgentKit repo root with the venv active.", file=sys.stderr)
        sys.exit(1)

    all_results: list[dict] = []
    new_count = 0

    for scenario in scenarios:
        sid = scenario["id"]

        if sid in done_ids:
            print(f"  SKIP (cached)  {sid:12s} | {scenario['domain']}")
            continue

        print(f"  RUNNING        {sid:12s} | {scenario['domain']:15s} | {scenario['query'][:55]}")
        t0 = time.perf_counter()

        try:
            res = analyze(scenario["query"])
            record = _score_result(scenario, res)
            record["latency_s"] = round(time.perf_counter() - t0, 3)
        except Exception as exc:  # noqa: BLE001
            record = {
                "id": sid,
                "domain": scenario["domain"],
                "query": scenario["query"],
                "passed": False,
                "tool_coverage": 0.0,
                "kw_coverage": 0.0,
                "has_report": False,
                "invoked_tools": [],
                "tools_hit": [],
                "report_length": 0,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "error": str(exc),
                "latency_s": round(time.perf_counter() - t0, 3),
            }
            print(f"    ERROR: {exc}")

        _append_cache(cache_file, record)
        done_ids.add(sid)
        all_results.append(record)
        new_count += 1

        status = "✅ PASS" if record["passed"] else "❌ FAIL"
        print(
            f"    {status} | tools={record['tool_coverage']:.0%} "
            f"| kw={record['kw_coverage']:.0%} "
            f"| report={record['report_length']}c "
            f"| {record['latency_s']:.2f}s"
        )

    # -----------------------------------------------------------------------
    # Load all cached results for summary (including prior runs)
    # -----------------------------------------------------------------------
    all_cached: list[dict] = []
    with cache_file.open() as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    all_cached.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

    # Per-domain aggregation
    domains: dict[str, list[dict]] = {}
    for r in all_cached:
        domains.setdefault(r.get("domain", "Unknown"), []).append(r)

    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)

    domain_scores: dict[str, float] = {}
    for domain, records in sorted(domains.items()):
        passed = sum(1 for r in records if r.get("passed"))
        total = len(records)
        pct = passed / total * 100 if total else 0
        domain_scores[domain] = pct
        print(f"  {domain:20s}  {passed}/{total}  ({pct:.1f}%)")

    total_passed = sum(1 for r in all_cached if r.get("passed"))
    total_all = len(all_cached)
    overall_pct = total_passed / total_all * 100 if total_all else 0

    print(f"\n  OVERALL: {total_passed}/{total_all} ({overall_pct:.1f}%)")
    print(f"  New results this run: {new_count}")

    summary = {
        "benchmark": "AgentKit multi-domain DSPy evaluation",
        "total_scenarios": total_all,
        "passed": total_passed,
        "failed": total_all - total_passed,
        "overall_pct": round(overall_pct, 2),
        "per_domain": {
            domain: {
                "passed": sum(1 for r in records if r.get("passed")),
                "total": len(records),
                "pct": round(domain_scores[domain], 2),
            }
            for domain, records in domains.items()
        },
        "cache_file": str(cache_file),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    # Write summary JSON alongside the cache
    summary_path = cache_file.parent / "agentkit_eval_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2))
    print(f"\nSummary written to: {summary_path}")

    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="AgentKit multi-domain DSPy benchmark")
    parser.add_argument(
        "--scenarios",
        type=Path,
        default=DEFAULT_SCENARIOS,
        help="Path to multi_domain_scenarios.json",
    )
    parser.add_argument(
        "--cache-file",
        type=Path,
        default=DEFAULT_CACHE,
        help="Path to .jsonl cache file for resumption",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would run without making API calls",
    )
    args = parser.parse_args()
    run_dspy_eval(
        scenarios_file=args.scenarios,
        cache_file=args.cache_file,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
