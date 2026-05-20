"""
AgentKit demo — 3-agent crew via CrewAI.

The CrewAI agents wrap the same MCP tools as @tool decorators.
"""
from __future__ import annotations

import asyncio
import os

from core.logger import get_logger

log = get_logger(__name__)

try:
    from crewai import Agent, Crew, Task  # type: ignore
    from crewai.tools import tool  # type: ignore
    _CREW = True
except ImportError:
    _CREW = False
    log.warning("crewai not installed — demo unavailable")


from mcp_server import query_kpis, get_company_health, get_executive_summary  # noqa: E402


def _sync(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


if _CREW:
    @tool("query_kpis")
    def t_query_kpis(domain: str = "Finance", limit: int = 20) -> str:
        return str(_sync(query_kpis(domain=domain, limit=limit)))

    @tool("get_company_health")
    def t_health(domain: str = "") -> str:
        return str(_sync(get_company_health(domain=domain or None)))

    @tool("get_executive_summary")
    def t_summary() -> str:
        return str(_sync(get_executive_summary()))


def build_crew():
    if not _CREW:
        return None
    researcher = Agent(
        role="Researcher",
        goal="Collect KPI data relevant to the business question",
        backstory="Senior data analyst with deep KPI knowledge",
        tools=[t_query_kpis, t_health, t_summary],
        verbose=True,
    )
    analyst = Agent(
        role="Analyst",
        goal="Identify patterns, anomalies and risks from KPI data",
        backstory="Strategic business analyst with finance background",
        verbose=True,
    )
    reporter = Agent(
        role="Reporter",
        goal="Produce an executive briefing",
        backstory="Senior executive communications lead",
        verbose=True,
    )

    task1 = Task(description="Gather KPI evidence for the question.", agent=researcher, expected_output="KPI data dump")
    task2 = Task(description="Interpret the data.", agent=analyst, expected_output="Findings and anomalies")
    task3 = Task(description="Write the executive briefing.", agent=reporter, expected_output="Final report")

    return Crew(agents=[researcher, analyst, reporter], tasks=[task1, task2, task3], verbose=True)


if __name__ == "__main__":
    crew = build_crew()
    if crew is None:
        print("crewai not installed. pip install crewai")
    else:
        result = crew.kickoff()
        print(result)
