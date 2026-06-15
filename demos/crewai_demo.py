"""
AgentKit demo — 3-agent crew via CrewAI.

The CrewAI agents wrap AgentKit's MCP tools as @tool functions and run a
Researcher → Analyst → Reporter crew. Uses Groq by default (LLM_DEFAULT);
set LLM_DEFAULT to any LiteLLM model to switch providers.

Run:  python demos/crewai_demo.py
"""
from __future__ import annotations

import asyncio
import os

from core.logger import get_logger

log = get_logger(__name__)

try:
    from crewai import LLM, Agent, Crew, Task  # type: ignore
    from crewai.tools import tool  # type: ignore
    _CREW = True
except ImportError:
    _CREW = False
    log.warning("crewai not installed — demo unavailable")


from mcp_server import get_company_health, get_executive_summary, query_kpis  # noqa: E402


def _sync(coro):
    """Run an async MCP tool from CrewAI's synchronous tool context (fresh loop)."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


if _CREW:
    @tool("query_kpis")
    def t_query_kpis(domain: str = "Finance", limit: int = 20) -> str:
        """Return the latest KPI metrics for a business domain (Finance, People, IT, …)."""
        return str(_sync(query_kpis(domain=domain, limit=limit)))

    @tool("get_company_health")
    def t_health(domain: str = "") -> str:
        """Return the composite company health index (score + interpretation) for a domain or all."""
        return str(_sync(get_company_health(domain=domain or None)))

    @tool("get_executive_summary")
    def t_summary() -> str:
        """Return a one-shot executive summary: health, key metrics, and anomalies."""
        return str(_sync(get_executive_summary()))


def _llm():
    """CrewAI LLM via LiteLLM. Defaults to Claude Haiku: CrewAI injects prompt-cache
    breakpoints that Groq rejects, so a cache-aware provider (Anthropic) is the safe default.
    Override with CREWAI_LLM."""
    return LLM(model=os.getenv("CREWAI_LLM", "anthropic/claude-haiku-4-5"))


def build_crew(question: str):
    if not _CREW:
        return None
    llm = _llm()
    researcher = Agent(
        role="Researcher", goal="Collect KPI data relevant to the business question",
        backstory="Senior data analyst with deep KPI knowledge",
        tools=[t_query_kpis, t_health, t_summary], llm=llm, verbose=False,
    )
    analyst = Agent(
        role="Analyst", goal="Identify patterns, anomalies and risks from KPI data",
        backstory="Strategic business analyst with a finance background", llm=llm, verbose=False,
    )
    reporter = Agent(
        role="Reporter", goal="Produce a concise executive briefing",
        backstory="Senior executive communications lead", llm=llm, verbose=False,
    )
    task1 = Task(description=f"Use the tools to gather KPI evidence for: '{question}'.",
                 agent=researcher, expected_output="Relevant KPI figures and the company health score")
    task2 = Task(description="Interpret the gathered data — patterns, anomalies, risks.",
                 agent=analyst, expected_output="3-5 bullet findings with numbers")
    task3 = Task(description="Write a short executive briefing (key finding, evidence, recommendation).",
                 agent=reporter, expected_output="A 4-6 sentence executive briefing")
    return Crew(agents=[researcher, analyst, reporter], tasks=[task1, task2, task3], verbose=False)


if __name__ == "__main__":
    crew = build_crew("How healthy is the business and what should leadership watch?")
    if crew is None:
        print("crewai not installed. pip install crewai")
    else:
        print(crew.kickoff())
