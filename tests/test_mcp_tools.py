"""Smoke tests for AgentKit MCP tools."""
import asyncio
import pytest


def test_imports():
    """All critical modules import cleanly."""
    from agentkit_mcp.core import config, logger
    import mcp_server
    assert mcp_server is not None


def test_settings_loaded():
    """Settings reads env vars with safe defaults."""
    from agentkit_mcp.core.config import settings
    assert settings.LLM_DEFAULT
    assert settings.LLM_REASONING


@pytest.mark.asyncio
async def test_query_kpis_returns_dict():
    """query_kpis returns a dict (stub-mode is acceptable)."""
    from mcp_server import query_kpis
    r = await query_kpis(domain="Finance")
    assert isinstance(r, dict)
    assert "kpis" in r and "total" in r


@pytest.mark.asyncio
async def test_get_company_health_returns_dict():
    from mcp_server import get_company_health
    r = await get_company_health()
    assert isinstance(r, dict)
    assert "score" in r


@pytest.mark.asyncio
async def test_detect_anomalies_returns_dict():
    from mcp_server import detect_kpi_anomalies
    r = await detect_kpi_anomalies(domain="Finance")
    assert isinstance(r, dict)
    assert "anomalies" in r


@pytest.mark.asyncio
async def test_forecast_metric_returns_dict():
    from mcp_server import forecast_metric
    r = await forecast_metric("revenue", periods=3)
    assert isinstance(r, dict)
    assert "forecast" in r


@pytest.mark.asyncio
async def test_list_metrics_returns_dict():
    from mcp_server import list_available_metrics
    r = await list_available_metrics()
    assert isinstance(r, dict)
    assert "metrics" in r and "categories" in r and "periods" in r


@pytest.mark.asyncio
async def test_executive_summary_returns_dict():
    from mcp_server import get_executive_summary
    r = await get_executive_summary()
    assert isinstance(r, dict)
    assert "summary" in r and "health_score" in r


def test_workflow_analyze_returns_dict():
    """workflow.analyze() always returns a dict (even in stub mode)."""
    from agentkit_mcp.workflow import analyze
    r = analyze("What's our company health?")
    assert isinstance(r, dict)
    assert "question" in r
